import inspect
import logging
import time
import types
from enum import Enum
from importlib import import_module
from pkgutil import iter_modules
from threading import Event
from typing import Callable, Optional

import pywf

MILLION = 1000000


def now_ms():
    return int(time.time() * MILLION)


def create_timer_task(
    microseconds: int,
    callback: Optional[Callable[[pywf.cpp_pyworkflow.TimerTask], None]],
    step: Optional[int] = None,
    cancel: Optional[Event] = None,  # [TODO] not proper type
) -> pywf.cpp_pyworkflow.TimerTask:
    if cancel is None:
        return pywf.create_timer_task(microseconds, callback)
    if isinstance(step, int):
        if step >= microseconds:
            raise ValueError(
                f"microseconds({microseconds}) should greater than step({step})"
            )
    else:
        step = MILLION / 3
    step = int(step)

    def _wrap_callback(task):
        if cancel and cancel.is_set():
            return
        callback(task)

    if microseconds <= step:
        return pywf.create_timer_task(microseconds, _wrap_callback)

    flags = {"first": True}

    def _callback(task):
        if cancel and cancel.is_set():
            return

        if flags["first"]:
            flags["first"] = False
            ud = task.get_user_data()
            task.set_user_data(
                {"_user_data": ud, "_expire_time": now_ms() + microseconds - step}
            )
        ud = task.get_user_data()
        left = ud["_expire_time"] - now_ms()
        t = None
        if left <= step:
            t = pywf.create_timer_task(left, _wrap_callback)
            t.set_user_data(ud["_user_data"])
        else:
            t = pywf.create_timer_task(step, _callback)
            t.set_user_data(ud)

        series = pywf.series_of(task)
        series << t

    return pywf.create_timer_task(step, _callback)


def kv_from_string(s):
    c = s.find(":")
    if c < 0:
        return (s, "")
    return (s[:c], s[c + 1 :])


def wf_error_string(state, code):
    return pywf.get_error_string(state, code)


class StrEnum(str, Enum):
    """Enum where members are also (and must be) string"""


class LogLevel(StrEnum):
    critical = "critical"
    error = "error"
    warning = "warning"
    info = "info"
    debug = "debug"


def init_logging(level):
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def vars_from_module(module, pass_func=None):
    def all_pass(v):
        return True

    if pass_func is None:
        pass_func = all_pass

    return dict([(v, getattr(module, v)) for v in dir(module) if pass_func(v)])


def is_public_upper(v):
    return not v.startswith("_") and v.isupper()


def walk_modules(module_path, skip_fail=True):

    mod = None
    try:
        mod = import_module(module_path)
        yield mod
    except Exception as e:
        if not skip_fail:
            raise e

    if mod and hasattr(mod, "__path__"):
        for _, subpath, _ in iter_modules(mod.__path__):
            fullpath = ".".join((module_path, subpath))
            for m in walk_modules(fullpath, skip_fail):
                yield m


def expected_cls(module, cls, base_class, include_base_class=False):
    if (
        inspect.isclass(cls)
        and issubclass(cls, base_class)
        and cls.__module__ == module.__name__
        and (
            include_base_class
            or (
                all([cls != base for base in base_class])
                if isinstance(base_class, tuple)
                else cls != base_class
            )
        )
    ):
        return True
    return False


def load_obj(obj_path, package=None):
    module_path, obj_name = obj_path.rsplit(".", 1)
    module = import_module(module_path, package=package)
    return getattr(module, obj_name, None)


def load_class(class_path, base_class, include_base_class=False, package=None):
    module_path, class_name = class_path.rsplit(".", 1)
    module = import_module(module_path, package=package)
    cls = getattr(module, class_name)
    if expected_cls(module, cls, base_class, include_base_class):
        return cls
    return None


def load_module_from_pyfile(filename):
    module = types.ModuleType("config")
    module.__file__ = filename
    try:
        with open(filename) as config_file:
            exec(compile(config_file.read(), filename, "exec"), module.__dict__)
    except IOError as e:
        e.strerror = "Unable to load configuration file (%s)" % e.strerror
        raise
    return module
