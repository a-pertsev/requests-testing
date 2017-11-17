# coding: utf-8

from __future__ import (absolute_import, print_function, division,
                        unicode_literals)

from requests.exceptions import ConnectionError

import pytest
import requests
import requests_testing


@requests_testing.activate
def test_simple_body():
    requests_testing.add(request={'url': 'http://example.com'}, response={'body': 'ok'})
    resp = requests.get('http://example.com')

    assert resp.text == 'ok'
    assert len(requests_testing.calls) == 1
    assert requests_testing.calls[0].request.url == 'http://example.com/'


@requests_testing.activate
def test_default_error():
    requests_testing.add(request={'url': 'http://example.com'})

    with pytest.raises(ConnectionError):
        requests.get('http://example.com/foo')

    assert len(requests_testing.calls) == 1
    assert requests_testing.calls[0].request.url == 'http://example.com/foo'
    assert type(requests_testing.calls[0].response) is ConnectionError
    requests.get('http://example.com')


@requests_testing.activate
def test_arbitrary_status_code():
    url = 'http://example.com/'
    requests_testing.add(request={'url': url}, response={'body': 'test', 'status': 418})
    resp = requests.get(url)
    assert resp.status_code == 418
    assert resp.reason is None


@requests_testing.activate
def test_response_cookies():
    body = 'test'
    status = 200
    headers = {'set-cookie': 'session_id=12345; a=b; c=d'}
    url = 'http://example.com/'

    requests_testing.add(request={'url': url, 'headers': headers}, response={'body': body})
    resp = requests.get(url, headers=headers)
    assert resp.text == body
    assert resp.status_code == status
    assert 'session_id' in resp.cookies
    assert resp.cookies['session_id'] == '12345'
    assert resp.cookies['a'] == 'b'
    assert resp.cookies['c'] == 'd'


@requests_testing.activate
def test_arbitrary_headers():
    body = 'test'
    status = 200
    req_headers = {'some-header': 'request'}
    mismatch_headers = {'some': 'request'}
    response_headers = {'some-header': 'response'}
    url = 'http://example.com/'

    requests_testing.add(request={'url': url, 'headers': req_headers},
                         response={'body': body, 'headers': response_headers})

    with pytest.raises(ConnectionError):
        requests.get('http://example.com/', headers=mismatch_headers)

    resp = requests.get(url, headers=req_headers)
    assert resp.text == body
    assert resp.status_code == status
    assert resp.headers == response_headers


@requests_testing.activate
def test_handles_unicode_url():
    url = u'http://www.संजाल.भारत/hi/वेबसाइट-डिजाइन'
    requests_testing.add(request={'url': url}, response={'body': 'ok'})
    resp = requests.get(url)

    assert resp.text == 'ok'
    assert len(requests_testing.calls) == 1


@requests_testing.activate
def test_handles_unicode_querystring():
    url = u'http://example.com/test?type=2&ie=utf8&query=汉字'
    requests_testing.add(request={'url': url}, response={'body': 'ok'})
    resp = requests.get(url)
    assert resp.text == 'ok'


@requests_testing.activate
def test_query_mismatch():
    url = u'http://example.com/test?type=2&ie=utf8&query=汉字'
    mismatch_url = u'http://example.com/test?type=2&ie=utf8&query=汉'
    requests_testing.add(request={'url': mismatch_url}, response={'body': 'ok'})

    with pytest.raises(ConnectionError):
        requests.get(url)

    requests.get(mismatch_url)


methods = [('GET', requests.get), ('POST', requests.post), ('PUT', requests.put)]


@pytest.mark.parametrize('method_name, method', methods)
def test_http_method_match(method_name, method):
    @requests_testing.activate
    def run():
        url = u'http://example.com/test'
        requests_testing.add(request={'url': url, 'method': method_name}, response={'body': 'ok'})
        resp = method(url)
        assert resp.text == 'ok'
    run()


@requests_testing.activate
def test_multiple_urls():
    requests_testing.add(request={'url': 'http://example.com/one'}, response={'body': 'one ok'})
    requests_testing.add(request={'url': 'http://example.com/two'}, response={'body': 'two ok'})

    resp = requests.get('http://example.com/one')
    assert resp.text == 'one ok'

    resp = requests.get('http://example.com/two')
    assert resp.text == 'two ok'


@requests_testing.activate
def test_default_calls_limit():
    requests_testing.add(request={'url': 'http://example.com/one'})

    requests.get('http://example.com/one')

    with pytest.raises(ConnectionError):
        requests.get('http://example.com/one')


@requests_testing.activate
def test_default_calls_limit_param():
    requests_testing.add(request={'url': 'http://example.com/one'}, calls_limit=2)

    requests.get('http://example.com/one')
    requests.get('http://example.com/one')

    with pytest.raises(ConnectionError):
        requests.get('http://example.com/one')


@requests_testing.activate
def test_multiple_responses():
    requests_testing.add(request={'url': 'http://example.com'}, response={'body': 'one ok'})
    requests_testing.add(request={'url': 'http://example.com'}, response={'body': 'two ok'})

    resp = requests.get('http://example.com')
    assert resp.text == 'one ok'

    resp = requests.get('http://example.com')
    assert resp.text == 'two ok'


@requests_testing.activate
def test_sugar_arguments():
    requests_testing.add('http://example.com/one', 'one ok')
    resp = requests.get('http://example.com/one')
    assert resp.text == 'one ok'


def test_passthru(httpserver):
    httpserver.serve_content('local OK', headers={'Content-Type': 'text/plain'})

    @requests_testing.activate
    def run():
        requests_testing.add(request={'url': httpserver.url}, response={'passthru': True})
        resp = requests.get(httpserver.url)
        assert resp.text == 'local OK'
    run()


def test_check_not_called_request():
    @requests_testing.activate
    def run():
        requests_testing.add('http://example.com', 'ok')

    with pytest.raises(requests_testing.NotCalledRequestException):
        run()


def test_check_not_called_request_does_not_swallow_exceptions():
    @requests_testing.activate
    def run():
        requests_testing.add('http://example.com', 'ok')
        raise AssertionError('test')

    with pytest.raises(AssertionError):
        run()
