import logging
import threading
from datetime import timedelta
from io import BytesIO
from typing import Any, Union
from urllib.parse import urljoin, urlparse

import pywf
from requests import PreparedRequest, Request, Response
from requests._internal_utils import to_native_string
from requests.auth import _basic_auth_str
from requests.compat import cookielib
from requests.cookies import RequestsCookieJar, cookiejar_from_dict, merge_cookies
from requests.exceptions import (
    ChunkedEncodingError,
    ContentDecodingError,
    TooManyRedirects,
)
from requests.hooks import default_hooks, dispatch_hook
from requests.models import DEFAULT_REDIRECT_LIMIT
from requests.sessions import (
    SessionRedirectMixin,
    merge_hooks,
    merge_setting,
    preferred_clock,
)
from requests.status_codes import codes
from requests.structures import CaseInsensitiveDict
from requests.utils import (
    get_auth_from_url,
    get_encoding_from_headers,
    prepend_scheme_if_needed,
    requote_uri,
    rewind_body,
    select_proxy,
)
from urllib3.response import HTTPResponse
from urllib3.util import parse_url

import os_pywf
from os_pywf.exceptions import Failure, WFException
from os_pywf.utils import MILLION, create_timer_task, extract_cookies_to_jar

HTTP_10 = "HTTP/1.0"
HTTP_11 = "HTTP/1.1"

logger = logging.getLogger(__name__)

session_redirect_mixin = SessionRedirectMixin()
session_redirect_mixin.trust_env = False


def default_user_agent():
    return f"os-pywf/{os_pywf.__version__}"


def default_headers():
    return CaseInsensitiveDict(
        {
            "User-Agent": default_user_agent(),
            # "Accept-Encoding": ", ".join(("gzip", "deflate")),
            # "Accept": "*/*",
            # "Connection": "keep-alive",
        }
    )


def _build_response(
    task: pywf.HttpTask, request: PreparedRequest
) -> Union[Response, Failure]:
    response = Response()
    response.url = request.url
    response.request = request

    if task.get_state() != 0:
        return Failure(WFException(task.get_state(), task.get_error()), response)

    resp = task.get_resp()

    response.status_code = int(resp.get_status_code())
    headers = dict(resp.get_headers())
    response.headers = CaseInsensitiveDict(headers)
    response.encoding = get_encoding_from_headers(response.headers)
    response.reason = resp.get_reason_phrase()
    extract_cookies_to_jar(response.cookies, request, response)
    raw = HTTPResponse(
        headers=headers,
        body=BytesIO(resp.get_body()),
        preload_content=False,
        request_method=request.method,
    )
    response.raw = raw

    return response


def build_response(
    task: pywf.HttpTask, request: PreparedRequest
) -> Union[Response, Failure]:
    try:
        return _build_response(task, request)
    except Exception as e:
        return Failure(e, None)


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

    def __init__(
        self,
        version=HTTP_11,
        headers=None,
        cookies=None,
        auth=None,
        proxies=None,
        hooks=None,
        params=None,
        allow_redirects=True,
        max_redirects=DEFAULT_REDIRECT_LIMIT,
        timeout=None,
        disable_keepalive=False,
        max_retries=0,
        retry_delay=0,
        max_size=None,
        callback=None,
        errback=None,
    ):
        self.headers = default_headers() if headers is None else headers
        self.cookies = cookiejar_from_dict({}) if cookies is None else cookies
        self.auth = auth
        self.proxies = {} if proxies is None else proxies
        self.hooks = default_hooks() if hooks is None else hooks
        self.params = {} if params is None else params
        self.allow_redirects = allow_redirects
        self.max_redirects = max_redirects
        self.timeout = timeout
        self.cancel_event = threading.Event()
        self.disable_keepalive = disable_keepalive
        self.version = version
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.max_size = max_size
        self.callback = callback
        self.errback = errback

    def cancel(self):
        if not self.canceled():
            self.cancel_event.set()

    def canceled(self):
        return self.cancel_event.is_set()

    def wait_cancel(self):
        if not self.canceled():
            self.cancel_event.wait()

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
        return self._request(req, **kwargs)

    def _request(self, request: Request, **kwargs):
        prep = self.prepare_request(request)
        return self.send(prep, **kwargs)

    def retry(self, task, request, **kwargs):
        retry_delay = kwargs.get("retry_delay", self.retry_delay)
        if retry_delay > 0:

            def _retry(t):
                s = pywf.series_of(t)
                n = self.send(
                    request,
                    **kwargs,
                )
                n.set_user_data(t.get_user_data())
                s.push_front(n)

            t = create_timer_task(
                retry_delay * MILLION, _retry, cancel=self.cancel_event
            )
        else:
            t = self.send(request, **kwargs)
        udata = task.get_user_data()
        retries = udata.get("_retries", 1)
        udata["_retries"] = retries + 1
        t.set_user_data(udata)
        series = pywf.series_of(task)
        series.push_front(t)

    def redirect(self, task, request, response, **kwargs):
        url = session_redirect_mixin.get_redirect_target(response)
        previous_fragment = urlparse(request.url).fragment
        prepared_request = request.copy()

        try:
            response.content
        except (ChunkedEncodingError, ContentDecodingError, RuntimeError):
            response.raw.read(decode_content=False)
        response.close()
        if url.startswith("//"):
            parsed_rurl = urlparse(resp.url)
            url = ":".join([to_native_string(parsed_rurl.scheme), url])
        parsed = urlparse(url)
        if parsed.fragment == "" and previous_fragment:
            parsed = parsed._replace(fragment=previous_fragment)
        elif parsed.fragment:
            previous_fragment = parsed.fragment
        url = parsed.geturl()

        if not parsed.netloc:
            url = urljoin(response.url, requote_uri(url))
        else:
            url = requote_uri(url)

        prepared_request.url = to_native_string(url)
        session_redirect_mixin.rebuild_method(prepared_request, response)
        if response.status_code not in (
            codes.temporary_redirect,
            codes.permanent_redirect,
        ):
            purged_headers = ("Content-Length", "Content-Type", "Transfer-Encoding")
            for header in purged_headers:
                prepared_request.headers.pop(header, None)
            prepared_request.body = None

        headers = prepared_request.headers
        headers.pop("Cookie", None)

        extract_cookies_to_jar(prepared_request._cookies, request, response)
        merge_cookies(prepared_request._cookies, self.cookies)
        prepared_request.prepare_cookies(prepared_request._cookies)
        session_redirect_mixin.rebuild_auth(prepared_request, response)
        rewindable = prepared_request._body_position is not None and (
            "Content-Length" in headers or "Transfer-Encoding" in headers
        )

        if rewindable:
            rewind_body(prepared_request)

        udata = task.get_user_data()
        t = self.send(prepared_request, **kwargs)
        t.set_user_data(udata)
        series = pywf.series_of(task)
        series.push_front(t)

    def send(
        self,
        request: PreparedRequest,
        **kwargs: Any,
    ) -> pywf.HttpTask:

        if isinstance(request, Request):
            return self._request(reqeust, **kwargs)

        extras = {"_start": preferred_clock()}  # [TODO] not the real start time

        def _callback(task):
            if self.canceled():
                series = pywf.series_of(task)
                if not series.is_canceled():
                    series.cancel()
                return
            udata = task.get_user_data()
            if not isinstance(udata, dict) or (
                "_user_data" not in udata and "_request" not in udata
            ):
                task.set_user_data({"_user_data": udata, "_request": request})
            elapsed = preferred_clock() - extras["_start"]
            response = build_response(task, request)
            udata = task.get_user_data()
            do = kwargs.get("callback", self.callback)
            if isinstance(response, Failure):  # [TODO] ignore specified exceptions
                response.value.elapsed = timedelta(seconds=elapsed)
                do = kwargs.get("errback", self.errback)
                if do is None:
                    do = kwargs.get("callback", self.callback)
                retries = udata.get("_retries", 1)
                if retries < kwargs.get("max_retries", self.max_retries):
                    self.retry(task, request, **kwargs)
                    do = None
            else:
                response.elapsed = timedelta(seconds=elapsed)
                response = dispatch_hook("response", request.hooks, response, **kwargs)
                if response.history:
                    for resp in response.history:
                        extract_cookies_to_jar(self.cookies, resp.request, resp)

                extract_cookies_to_jar(self.cookies, request, response)
                history = udata.get("_history", [])
                udata["_history"] = history
                if not response.is_redirect:
                    response.history = history
                    response.content
                elif kwargs.get("allow_redirects", self.allow_redirects):
                    history.append(response)
                    response.history = history[:-1]
                    max_redirects = kwargs.get("max_redirects", self.max_redirects)
                    if len(response.history) < max_redirects:
                        self.redirect(task, request, response, **kwargs)
                        do = None
                    else:
                        do = kwargs.get("errback", self.errback)
                        if do is None:
                            do = kwargs.get("callback", self.callback)
                        response = Failure(
                            TooManyRedirects(
                                "exceeded {} redirects".format(max_redirects),
                                response=response,
                            ),
                            response,
                        )

            if do:
                _request = udata["_request"]
                task.set_user_data(udata["_user_data"])
                results = None
                try:
                    results = do(task, _request, response)
                except Exception as e:
                    logger.error(
                        f"unexpected exception from {do.__module__}.{do.__name__} {e}"
                    )

                def _task(t):
                    if isinstance(t, str):
                        return self.get(t)
                    elif isinstance(t, PreparedRequest):
                        return self.send(t)  # send without session param
                    elif isinstance(t, Request):
                        return self.send(t)
                    elif isinstance(t, pywf.SubTask):
                        return t
                    logger.warn(f"not supported type {type(t)}")

                def _tasks(s):
                    r = []
                    if isinstance(s, list):
                        r = [_task(t) for t in s]
                    r = [_task(s)]
                    return [t for t in r if t is not None]

                if results is None:
                    return
                pre, post = [], []
                if isinstance(results, tuple):
                    l = len(results)
                    if l >= 1:
                        pre = _tasks(results[0])
                    if l >= 2:
                        post = _tasks(results[1])
                else:
                    pre = _tasks(results)
                series = pywf.series_of(task)
                list(map(series.push_front, pre[::-1]))
                list(map(series.push_back, post))

        return self.create_http_task(request, _callback, **kwargs)

    def create_http_task(self, request: PreparedRequest, cb, **kwargs) -> pywf.HttpTask:
        proxies = kwargs.get("proxies", self.proxies)
        proxy = select_proxy(request.url, proxies)
        request_url_parsed = None
        if not proxy:
            task = pywf.create_http_task(request.url, 0, 0, cb)
        else:
            request_url_parsed = urlparse(request.url)
            request_scheme = request_url_parsed.scheme.lower()
            if request_scheme != "http":
                raise NotImplementedError(f"Not support proxy for {request_scheme}")

            proxy = prepend_scheme_if_needed(proxy, "http")
            proxy_url_parsed = parse_url(proxy)
            proxy_scheme = proxy_url_parsed.scheme.lower()
            if proxy_scheme != "http":
                raise NotImplementedError(f"Not support {proxy_scheme} proxy")

            task = pywf.create_http_task(proxy_url_parsed.url, 0, 0, cb)
            # should remove auth from url?
            # request.url = urldefragauth(request.url)

        timeout = kwargs.get("timeout", self.timeout)
        if timeout:
            if isinstance(timeout, tuple):
                pass
            elif isinstance(timeout, int):
                timeout = (timeout, timeout)
            else:
                raise ValueError("timeout must be None tuple or int")
            if timeout[0] >= 0:
                task.set_send_timeout(timeout[0] * MILLION)
            if timeout[1] >= 0:
                task.set_receive_timeout(timeout[1] * MILLION)

        task.set_keep_alive(
            0 if kwargs.get("disable_keepalive", self.disable_keepalive) else 1
        )
        req = task.get_req()
        req.set_method(request.method)
        if request.body:
            req.append_body(request.body)
        req.set_http_version(kwargs.get("version", self.version))
        for k, v in request.headers.items():
            req.set_header_pair(k, v)
        max_size = kwargs.get("max_size", self.max_size)
        if max_size is not None:
            resp = task.get_resp()
            resp.set_size_limit(max_size)
        if proxy:
            req.set_request_uri(request.url)
            username, password = get_auth_from_url(proxy)
            if username:
                req.set_header_pair(
                    "Proxy-Authorization", _basic_auth_str(username, password)
                )
            req.set_header_pair("Host", request_url_parsed.netloc)
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


def request(
    url,
    method="GET",
    **kwargs,
):
    with Session() as session:
        return session.request(url, method=method, **kwargs)


def get(url, params=None, **kwargs):
    kwargs.pop("method", None)
    return request(url, method="GET", params=params, **kwargs)


def options(url, **kwargs):
    kwargs.pop("method", None)
    return request(url, method="OPTIONS", **kwargs)


def head(url, **kwargs):
    kwargs.pop("method", None)
    kwargs.setdefault("allow_redirects", False)
    return request(url, method="HEAD", **kwargs)


def post(url, data=None, json=None, **kwargs):
    kwargs.pop("method", None)
    return request(url, method="POST", data=data, json=json, **kwargs)


def put(url, data=None, **kwargs):
    kwargs.pop("method", None)
    return request(url, method="PUT", data=data, **kwargs)


def patch(url, data=None, **kwargs):
    kwargs.pop("method", None)
    return request(url, method="PATCH", data=data, **kwargs)


def delete(url, **kwargs):
    kwargs.pop("method", None)
    return request(url, method="DELETE", data=data, **kwargs)
