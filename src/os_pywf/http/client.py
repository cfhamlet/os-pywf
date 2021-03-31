import pywf
from requests import Request

HTTP_10 = "HTTP/1.0"
HTTP_11 = "HTTP/1.1"


def response_from_task(task):
    pass


def request(
    url,
    method="GET",
    version=HTTP_11,
    callback=None,
    errback=None,
    timeout=None,
    disable_keepalive=False,
    max_size=None,
    retry=0,
    retry_delay=0,
    max_redirs=20,
    **kwargs
):
    raw = Request(url=url, method=method, **kwargs)
    request = raw.prepare()
    send_timeout = 0
    receive_timeout = 0
    if timeout:
        if isinstance(timeout, int):
            send_timeout = timeout
        elif isinstance(timeout, tuple):
            send_timeout = 0 if timeout[0] is None else timeout[0]
            receive_timeout = 0 if timeout[1] is None else timeout[1]

    def _callback(task):
        series = pywf.series_of(task)
        context = series.get_context()
        if context is None:
            context = {}
            series.set_context(context)
        response = response_from_task(task)
        print(response)

    task = pywf.create_http_task(request.url, 0, 0, _callback)
    task.set_send_timeout(send_timeout)
    task.set_receive_timeout(receive_timeout)
    task.set_keep_alive(1 if disable_keepalive else 0)
    req = task.get_req()
    req.set_method(request.method)
    req.set_http_version(version)
    for k, v in request.headers.items():
        req.add_header_pair(k, v)

    if max_size is not None:
        req.set_size_limit(max_size)

    return task


def get(url, params=None, **kwargs):
    pass


def options(url, **kwargs):
    pass


def head(url, **kwargs):
    pass


def post(url, data=None, json=None, **kwargs):
    pass


def put(url, data=None, **kwargs):
    pass


def patch(url, data=None, **kwargs):
    pass


def delete(url, **kwargs):
    pass
