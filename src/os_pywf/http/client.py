import logging
from http.client import HTTPMessage
from io import BytesIO, StringIO
from typing import Union

import pywf
from requests import PreparedRequest, Request, Response
from requests.cookies import MockRequest, MockResponse
from requests.models import DEFAULT_REDIRECT_LIMIT
from requests.structures import CaseInsensitiveDict
from requests.utils import get_encoding_from_headers

from os_pywf.exceptions import WFException
from os_pywf.utils import MILLION, create_timer_task

HTTP_10 = "HTTP/1.0"
HTTP_11 = "HTTP/1.1"

logger = logging.getLogger(__name__)


def build_response(task, request: PreparedRequest) -> Union[Response, WFException]:
    if task.get_state() != 0:
        return WFException(task.get_state(), task.get_error())

    resp = task.get_resp()
    response = Response()

    response.status_code = resp.get_status_code()

    response.headers = CaseInsensitiveDict(dict(resp.get_headers()))
    response.encoding = get_encoding_from_headers(response.headers)

    response.raw = BytesIO(resp.get_body())
    response.reason = resp.get_reason_phrase()
    response.url = request.url
    response.request = request

    response.cookies.extract_cookies(
        MockResponse(
            HTTPMessage(
                StringIO(
                    "\r\n".join([f"{k}: {v}" for k, v in response.headers.items()])
                )
            )
        ),
        MockRequest(request),
    )

    return response


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
        if isinstance(timeout, tuple):
            pass
        elif isinstance(timeout, int):
            timeout = (timeout, 0)
        else:
            raise ValueError("timeout must be None tuple or int")
    else:
        timeout = (0, 0)
    kwargs["timeout"] = timeout
    cancel = kwargs.get("cancel", None)

    def _callback(task):
        udata = task.get_user_data()
        if not isinstance(udata, dict) or (
            "_user_data" not in udata and "_request" not in udata
        ):
            task.set_user_data({"_user_data": udata, "_request": request})
        series = pywf.series_of(task)
        context = series.get_context()
        if context is None:
            context = {"session": {}}
            series.set_context(context)
        response = build_response(task, request)
        udata = task.get_user_data()

        do = kwargs.get("callback", None)
        if isinstance(response, WFException):  # [TODO] ignore specified exceptions
            do = kwargs.get("errback", None)
            retries = udata.get("_retries", 1)
            if retries < kwargs.get("max_retries", 0):
                retry_delay = kwargs.get("retry_delay", 0)
                if retry_delay > 0:

                    def _retry(t):
                        s = pywf.series_of(t)
                        n = send(
                            request,
                            **kwargs,
                        )
                        n.set_user_data(t.get_user_data())
                        s << n

                    t = create_timer_task(retry_delay * MILLION, _retry, cancel=cancel)
                else:
                    t = send(request, **kwargs)
                udata["_retries"] = retries + 1
                t.set_user_data(udata)
                series << t
                do = None
        else:
            if response.is_redirect:
                redirects = udata.get("_redirects", 0)
                if kwargs.get("allow_redirects", True):
                    if redirects < kwargs.get("max_redirects", DEFAULT_REDIRECT_LIMIT):
                        udata["_redirect"] = redirects + 1
                        # [TODO]
                        do = None

        if do:
            req = udata["_request"]
            task.set_user_data(udata["_user_data"])
            try:
                do(task, req, response)
            except Exception as e:
                logger.error(
                    f"unexpected exception from {do.__module__}.{do.__name__} {e}"
                )

    task = pywf.create_http_task(request.url, 0, 0, _callback)
    if timeout[0] > 0:
        task.set_send_timeout(timeout[0] * MILLION)
    if timeout[1] > 0:
        task.set_receive_timeout(timeout[1] * MILLION)
    task.set_keep_alive(1 if kwargs.get("disable_keepalive", False) else 0)
    req = task.get_req()
    req.set_method(request.method)
    req.set_http_version(kwargs.get("version", HTTP_11))
    for k, v in request.headers.items():
        req.add_header_pair(k, v)
    max_size = kwargs.get("max_size", 0)
    if max_size is not None and max_size >= 0:
        resp = task.get_resp()
        resp.set_size_limit(max_size)
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
