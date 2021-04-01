import logging
from typing import Union

import pywf
from requests import Request, Response
from requests.models import DEFAULT_REDIRECT_LIMIT

from os_pywf.exceptions import WFException

HTTP_10 = "HTTP/1.0"
HTTP_11 = "HTTP/1.1"
MILLION = 1000000


logger = logging.getLogger(__name__)


def response_from_task(task) -> Union[Response, WFException]:
    if task.get_state() != 0:
        return WFException(task.get_state(), task.get_error())

    context = task.get_context()
    context = {} if context is None else context


def send(
    request,
    # timeout=None,
    # disable_keepalive=False,
    # max_size=None,
    # max_retries=0,
    # retry_delay=0,
    # max_redirects=DEFAULT_REDIRECT_LIMIT,
    # allow_redirects=True,
    # callback=None,
    # errback=None,
    **kwargs,
):
    timeout = kwargs.get("timeout", None)
    if timeout:
        if isinstance(timeout, int):
            timeout = (timeout, 0)
        elif isinstance(timeout, tuple):
            pass
        else:
            raise ValueError("timeout must be None tuple or int")
    else:
        timeout = (0, 0)
    kwargs["timeout"] = timeout

    def _callback(task):
        series = pywf.series_of(task)
        context = series.get_context()
        if context is None:
            context = {"session": {}}
            series.set_context(context)
        response = response_from_task(task)
        udata = task.get_user_data()

        do = kwargs.get("callback", None)
        if isinstance(response, WFException):
            do = kwargs.get("errback", None)
            retries = udata.get("retries", 0)
            if retries < kwargs.get("max_retries", 0):

                def _retry(t):
                    s = pywf.series_of(t)
                    n = send(
                        request,
                        **kwargs,
                    )
                    n.set_user_data(t.get_user_data())
                    s << n

                retry_delay = kwargs.get("retry_delay", 0)
                if retry_delay > 0:
                    t = pywf.create_timer_task(retry_delay * MILLION, _retry)
                else:
                    t = send(request, *kwargs)
                udata["retries"] = retries + 1
                t.set_user_data(udata)
                series << t
        else:
            if response.is_redirect():
                if kwargs.get("allow_redirects", True):
                    redirects = udata.get("redirects", 0)
                    if redirects < kwargs.get("max_redirects", DEFAULT_REDIRECT_LIMIT):
                        pass
                    else:
                        pass
                else:
                    pass  # do nothing
            else:
                pass  # do nothing

        if do:
            try:
                do(task, request, response)
            except Exception as e:
                logger.error(
                    f"unexpected exception from {do.__module__}.{do.__name__} {e}"
                )

    task = pywf.create_http_task(request.url, 0, 0, _callback)
    task.set_user_data({"request": request})
    task.set_send_timeout(timeout[0])
    task.set_receive_timeout(timeout[1])
    task.set_keep_alive(1 if kwargs.get("disable_keepalive", False) else 0)
    req = task.get_req()
    req.set_method(request.method)
    req.set_http_version(kwargs.get("version", HTTP_11))
    for k, v in request.headers.items():
        req.add_header_pair(k, v)

    max_size = kwargs.get("max_size", None)
    if max_size is not None:
        req.set_size_limit(max_size)

    return task


def request(
    url,
    method="GET",
    headers=None,
    files=None,
    data=None,
    params=None,
    auth=None,
    cookies=None,
    hooks=None,
    json=None,
    **kwargs,
):
    raw = Request(
        url=url,
        method=method,
        headers=headers,
        files=files,
        data=data,
        params=params,
        auth=auth,
        cookies=cookies,
        hooks=hooks,
        json=json,
    )
    request = raw.prepare()
    return send(
        request,
        **kwargs,
    )


def get(url, params=None, **kwargs):
    kwargs.pop("method", None)
    return request(url, params=params, **kwargs)


def options(url, **kwargs):
    kwargs.pop("method", None)
    return request(url, "OPTIONS", **kwargs)


def head(url, **kwargs):
    kwargs.pop("method", None)
    kwargs.setdefault("allow_redirects", False)
    return request(url, "HEAD", **kwargs)


def post(url, data=None, json=None, **kwargs):
    kwargs.pop("method", None)
    return request(url, "POST", data=data, json=json, **kwargs)


def put(url, data=None, **kwargs):
    kwargs.pop("method", None)
    return request(url, "PUT", data=data, **kwargs)


def patch(url, data=None, **kwargs):
    kwargs.pop("method", None)
    return request(url, "PATCH", data=data, **kwargs)


def delete(url, **kwargs):
    kwargs.pop("method", None)
    return request(url, "DELETE", data=data, **kwargs)
