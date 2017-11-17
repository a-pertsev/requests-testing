# coding: utf-8

from __future__ import (absolute_import, print_function, division,
                        unicode_literals)

import idna
from functools import wraps
from collections import namedtuple
from cookies import Cookies

import six
from requests.exceptions import ConnectionError
from requests.adapters import HTTPAdapter
from requests.utils import cookiejar_from_dict, requote_uri

if six.PY2:
    from urlparse import urlsplit, urlunparse, parse_qs
else:
    from urllib.parse import urlsplit, urlunparse, parse_qs

if six.PY2:
    try:
        from six import cStringIO as BufferIO
    except ImportError:
        from six import StringIO as BufferIO
else:
    from io import BytesIO as BufferIO

try:
    from requests.packages.urllib3.response import HTTPResponse
except ImportError:
    from urllib3.response import HTTPResponse

try:
    from unittest import mock
except ImportError:
    import mock


Call = namedtuple('Call', ('request', 'response'))


def _to_utf8_bytes(some):
    if six.PY2 and not isinstance(some, str):
        return some.encode('utf-8')
    return some


class NotCalledRequestException(BaseException):
    pass


class _ParsedRequest(object):
    def __init__(self, request_dict):
        self.url, self.query_params = self.parse_url(request_dict.get('url'))
        self.method = request_dict.get('method', 'GET')
        self.headers = request_dict.get('headers', {})

    def matches(self, real_request):
        if not self._url_and_query_matches(real_request.url):
            return False

        if not self._method_matches(real_request.method):
            return False

        if not self._headers_matches(real_request.headers):
            return False

        return True

    @staticmethod
    def parse_url(url):
        if url is None:
            return None, {}

        scheme, netloc, path, query, fragment = urlsplit(url)
        host, _, port = netloc.partition(':')
        host = str(idna.encode(host, uts46=True))
        netloc = '{}:{}'.format(host, port) if port else host
        path = '/' if not path else path
        scheme, netloc, path, query, fragment = map(_to_utf8_bytes,
                                                    (scheme, netloc, path, query, fragment))
        parsed_query = parse_qs(query)
        url = urlunparse((scheme, netloc, path, '', '', fragment))
        url = requote_uri(url)
        return url, parsed_query

    def _url_and_query_matches(self, url):
        if self.url is None:
            return True

        url, parsed_query = self.parse_url(url)
        if self.url != url:
            return False

        for k, v in self.query_params.items():
            if parsed_query.get(k) != v:
                return False

        return True

    def _method_matches(self, method):
        if self.method is None:
            return True
        return self.method == method

    def _headers_matches(self, headers):
        if self.headers is None:
            return True

        for header, value in self.headers.items():
            if headers.get(header) != value:
                return False

        return True


class MockedRequest(object):
    def __init__(self, request, response=None, calls_limit=1):
        if isinstance(request, six.string_types):
            request = {'url': request}

        if isinstance(response, six.string_types):
            response = {'body': response}

        self.request = _ParsedRequest(request)
        self.response = response if response is not None else {}

        self.calls_limit = calls_limit


class Mock(object):
    def __init__(self):
        self.calls = []
        self._mocked_requests = []
        self._patcher = None
        self._real_send = None

    def _add_call(self, req, resp):
        self.calls.append(Call(req, resp))

    def add(self, request, response=None, calls_limit=1):
        self._mocked_requests.append(MockedRequest(request, response, calls_limit))

    def _find_match(self, request):
        for i, mocked in enumerate(self._mocked_requests):
            if mocked.request.matches(request):
                if mocked.calls_limit is not None:
                    mocked.calls_limit -= 1
                    if mocked.calls_limit == 0:
                        self._mocked_requests.pop(i)
                return mocked

    def _on_request(self, adapter, request, **kwargs):
        mocked = self._find_match(request)

        if not mocked:
            error_msg = 'Connection refused: {} {}'.format(request.method, request.url)
            response = ConnectionError(error_msg)
            response.request = request
            self._add_call(request, response)
            raise response

        if mocked.response.get('passthru'):
            return self._real_send(adapter, request)

        status = mocked.response.get('status', six.moves.http_client.OK)
        body = mocked.response.get('body')
        body = BufferIO(body.encode('utf-8') if body is not None else body)
        response = HTTPResponse(
            status=status,
            reason=six.moves.http_client.responses.get(status),
            body=body,
            headers=mocked.response.get('headers'),
            preload_content=False
        )

        response = adapter.build_response(request, response)
        self._inject_cookies(request, response)
        self._add_call(request, response)
        return response

    @staticmethod
    def _inject_cookies(request, response):
        try:
            resp_cookies = Cookies.from_request(request.headers['set-cookie'])
            response.cookies = cookiejar_from_dict({
                v.name: v.value for _, v in resp_cookies.items()
            })
        except (KeyError, TypeError):
            pass

    def check_not_called(self):
        if self._mocked_requests:
            raise NotCalledRequestException(
                'Not all mocked requests have been called: %r',
                [(mock.request.method, mock.request.url)
                 for mock in self._mocked_requests]
            )

    def _stop(self, assert_not_called):
        self._patcher.stop()
        self.calls[:] = []

        try:
            if assert_not_called:
                self.check_not_called()
        except NotCalledRequestException:
            raise
        finally:
            self._mocked_requests = []

    def _start(self):
        self._real_send = HTTPAdapter.send
        self._patcher = mock.patch('requests.adapters.HTTPAdapter.send',
                                   lambda *a, **kw: self._on_request(*a, **kw))
        self._patcher.start()

    def __enter__(self):
        self._start()
        return self

    def __exit__(self, ex_type, value, traceback):
        success = ex_type is None
        self._stop(assert_not_called=success)
        return success


_mock = Mock()


def activate(fn):
    @wraps(fn)
    def new_fn(*args, **kwargs):
        with _mock:
            return fn(*args, **kwargs)

    return new_fn


add = _mock.add
calls = _mock.calls

__all__ = ['add', 'calls', 'activate']
