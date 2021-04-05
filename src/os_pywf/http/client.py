import logging
import threading
from http.client import HTTPMessage
from io import BytesIO, StringIO
from typing import Any, Union

import pywf
from requests import PreparedRequest, Request, Response
from requests.compat import cookielib
from requests.cookies import (
    MockRequest,
    MockResponse,
    RequestsCookieJar,
    cookiejar_from_dict,
    merge_cookies,
)
from requests.models import DEFAULT_REDIRECT_LIMIT
from requests.sessions import merge_hooks, merge_setting
from requests.structures import CaseInsensitiveDict
from requests.utils import get_encoding_from_headers

import os_pywf
from os_pywf.exceptions import WFException
from os_pywf.utils import MILLION, create_timer_task

HTTP_10 = "HTTP/1.0"
HTTP_11 = "HTTP/1.1"

logger = logging.getLogger(__name__)


def default_user_agent():
    return f"os-pywf/{os_pywf.__version__}"


def default_headers():
    return CaseInsensitiveDict(
        {
            "User-Agent": default_user_agent(),
            "Accept-Encoding": ", ".join(("gzip", "deflate")),
            "Accept": "*/*",
            "Connection": "keep-alive",
        }
    )


def build_response(
    task: pywf.HttpTask, request: PreparedRequest
) -> Union[Response, WFException]:
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


class Session(object):

    __attrs__ = [
        "headers",
        "cookies",
        "auth",
        "hooks",
        "params",
        "allow_redirects",
        "max_redirects",
        "timeout",
        "cancel_event",
        "disable_keepalive",
        "version",
        "max_retries",
        "retry_delay",
        "max_size",
        "callback",
        "errback",
    ]

    def __init__(self):
        self.headers = default_headers()
        self.cookies = cookiejar_from_dict({})
        self.auth = None
        self.hooks = default_hooks()
        self.params = {}
        self.allow_redirects = True
        self.max_redirects = DEFAULT_REDIRECT_LIMIT
        self.timeout = None
        self.cancel_event = threading.Event()
        self.disable_keepalive = False
        self.version = HTTP_11
        self.max_retries = 0
        self.retry_delay = 0
        self.max_size = None
        self.callback = None
        self.errback = None

    def cancel(self):
        if not self.cancelled():
            self.cancel_event.set()

    def cancelled(self):
        return self.cancel_event.is_set()

    def prepare_request(self, request: Request) -> PreparedRequest:

        cookies = request.cookies or {}

        if not isinstance(cookies, cookielib.CookieJar):
            cookies = cookiejar_from_dict(cookies)

        merged_cookies = merge_cookies(
            merge_cookies(RequestsCookieJar(), self.cookies), cookies
        )

        auth = request.auth

        p = PreparedRequest()
        p.prepare(
            method=request.method.upper(),
            url=request.url,
            files=request.files,
            data=request.data,
            json=request.json,
            headers=merge_setting(
                request.headers, self.headers, dict_class=CaseInsensitiveDict
            ),
            params=merge_setting(request.params, self.params),
            auth=merge_setting(auth, self.auth),
            cookies=merged_cookies,
            hooks=merge_hooks(request.hooks, self.hooks),
        )
        return p

    def request(
        self,
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
        req = Request(
            url=url,
            method=method.upper(),
            headers=headers,
            files=files,
            data=data or {},
            json=json,
            params=params or {},
            auth=auth,
            cookies=cookies,
            hooks=hooks,
        )
        prep = self.prepare_request(req)
        task = self.send(prep, **kwargs)
        return task

    def send(
        self,
        request: PreparedRequest,
        **kwargs: Any,
    ) -> pywf.HttpTask:

        if isinstance(request, Request):
            raise ValueError("You can only send PreparedRequests.")

        def _callback(task):
            if self.cancelled():
                return
            udata = task.get_user_data()
            if not isinstance(udata, dict) or (
                "_user_data" not in udata and "_request" not in udata
            ):
                task.set_user_data({"_user_data": udata, "_request": request})
            series = pywf.series_of(task)
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

                        t = create_timer_task(
                            retry_delay * MILLION, _retry, cancel=self.cancel_event
                        )
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
                        if redirects < kwargs.get(
                            "max_redirects", DEFAULT_REDIRECT_LIMIT
                        ):
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
        return self._prepare_task(task, request, **kwargs)

    def _prepare_task(
        self, task: pywf.HttpTask, request: PreparedRequest, **kwargs
    ) -> pywf.HttpTask:
        timeout = kwargs.get("timeout", self.timeout)
        if timeout:
            if isinstance(timeout, tuple):
                pass
            elif isinstance(timeout, int):
                timeout = (timeout, 0)
            else:
                raise ValueError("timeout must be None tuple or int")
            task.set_send_timeout(timeout[0] * MILLION)
            task.set_receive_timeout(timeout[1] * MILLION)

        task.set_keep_alive(
            1 if kwargs.get("disable_keepalive", self.disable_keepalive) else 0
        )
        req = task.get_req()
        req.set_method(request.method)
        req.set_http_version(kwargs.get("version", self.version))
        for k, v in request.headers.items():
            req.add_header_pair(k, v)
        max_size = kwargs.get("max_size", self.max_size)
        if max_size is not None:
            resp = task.get_resp()
            resp.set_size_limit(max_size)
        return task

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        pass

    def get(self, url, params=None, **kwargs):
        kwargs.pop("method", None)
        return self.request(url, params=params, **kwargs)

    def options(self, url, **kwargs):
        kwargs.pop("method", None)
        return self.request(url, method="OPTIONS", **kwargs)

    def head(self, url, **kwargs):
        kwargs.pop("method", None)
        kwargs.setdefault("allow_redirects", False)
        return self.request(self, url, method="HEAD", **kwargs)

    def post(self, url, data=None, json=None, **kwargs):
        kwargs.pop("method", None)
        return self.request(self, url, method="POST", data=data, json=json, **kwargs)

    def put(self, url, data=None, **kwargs):
        kwargs.pop("method", None)
        return self.request(self, url, method="PUT", data=data, **kwargs)

    def patch(self, url, data=None, **kwargs):
        kwargs.pop("method", None)
        return self.request(self, url, method="PATCH", data=data, **kwargs)

    def delete(self, url, **kwargs):
        kwargs.pop("method", None)
        return self.request(url, method="DELETE", data=data, **kwargs)


def session():
    return Session()


def request(
    url,
    method="GET",
    **kwargs,
):
    with Session() as session:
        return session.request(url, method=method, **kwargs)


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
