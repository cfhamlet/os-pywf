from os_pywf.utils import wf_error_string


class Failure(BaseException):
    def __init__(self, exception, value=None):
        self.exception = exception
        self.value = value

    def __str__(self):
        return f"{self.exception} {self.value}"


class WFException(Exception):
    def __init__(self, state, code):
        self.state = state
        self.code = code

    def __str__(self):
        return wf_error_string(self.state, self.code)
