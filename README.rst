Requests-testing
=========

.. image:: https://travis-ci.org/a-pertsev/requests-testing.svg?branch=master
    :target: https://travis-ci.org/a-pertsev/requests-testing

A utility library for mocking out the `requests` Python library.

Starting with requests-testing
------

Here is a simple example:

.. code-block:: python

    import requests
    import requests_testing


    @requests_testing.activate
    def example():
        requests_testing.add(request={'url': 'http://example.com'}, response={'body': 'ok'})
        resp = requests.get('http://example.com')

        assert resp.text == 'ok'
        assert len(requests_testing.calls) == 1
        assert requests_testing.calls[0].request.url == 'http://example.com/'

If your attempts to fetch a url which doesn't hit a match, ``ConnectionError`` will raise:

.. code-block:: python

    import requests
    import requests_testing

    from requests.exceptions import ConnectionError

    @responses.activate
    def test_error():
        with pytest.raises(ConnectionError):
            requests.get('http://example.com')

