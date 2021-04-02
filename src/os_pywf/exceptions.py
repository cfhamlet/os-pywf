from os_pywf.utils import wf_error_string


class WFException(Exception):
    def __init__(self, state, code):
        self.state = state
        self.code = code

    def __str__(self):
        return {wf_error_string(self.state, self.code)}
