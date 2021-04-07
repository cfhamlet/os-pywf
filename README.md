# os-pywf

[![Build Status](https://www.travis-ci.org/cfhamlet/os-pywf.svg?branch=master)](https://www.travis-ci.org/cfhamlet/os-pywf)
[![codecov](https://codecov.io/gh/cfhamlet/os-pywf/branch/master/graph/badge.svg)](https://codecov.io/gh/cfhamlet/os-pywf)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/os-pywf.svg)](https://pypi.python.org/pypi/os-pywf)
[![PyPI](https://img.shields.io/pypi/v/os-pywf.svg)](https://pypi.python.org/pypi/os-pywf)

[Workflow](https://github.com/sogou/workflow) it's Python binding [PyWorkflow](https://github.com/sogou/pyworkflow) are great async frameworks.

This project is trying to explore the power of the framework and provide command line tools and high level APIs for real world development.

## Install

```
pip install os-pywf
```


## Command line

``os-pywf`` command can be used after installation. There are several subcommands can be used. You can get help information of subcommands with ``--help`` option.  Global settings of Workflow can be specified, ENVs is not supported yet.

The subcommands with *planning* tag will be developed later, can not be used right now.

```
$ os-pywf
Usage: os-pywf [OPTIONS] COMMAND [ARGS]...

  Command line tool for os-pywf.

Options:
  --version                       Show the version and exit.
  Workflow:                       Workflow global settings.
    --compute-threads INTEGER     Number of compute threads.  [default: 4]
    --handler-threads INTEGER     Number of handler threads.  [default: 4]
    --poller-threads INTEGER      Number of poller threads.  [default: 4]
    --dns-threads INTEGER         Number of dns threads.  [default: 4]
    --dns-ttl-default INTEGER     Default seconds of dns ttl.  [default:
                                  43200]

    --dns-ttl-min INTEGER         Min seconds of dns ttl.  [default: 180]
    --max-connections INTEGER     Max number of connections.  [default: 200]
    --connection-timeout INTEGER  Connect timeout(ms).  [default: 10000]
    --response-timeout INTEGER    Response timeout(ms).  [default: 10000]
    --ssl-connect-timeout INTEGER
                                  SSL connect timeout(ms).  [default: 10000]
  --help                          Show this message and exit.

Commands:
  curl    HTTP client inspired by curl.
  mysql   MySQL client (planning).
  proxy   HTTP proxy (planning).
  redis   Redis client (planning).
  run     Run runnable objects of pywf (planning).
  spider  Web spider (planning).
  web     Web server (planning).
```



### curl

This subcommand is inspired by curl. It works as curl and provides more useful features especially invoke Python function as response callback, which make it flexible and easy to use.

Features:

* Same options as curl, can be used by curl directly
* Support HTTP version 1.0/1.1
* Auto manipulate cookies. Cookies can be spicified by command line or read from file. Cookies can be saved to file.
* Support post urlencode data
* Support upload files as multipart form
* Support redirect and response history saved in response.history
* Support retry and retry interval.  The program can be quickly cancelled when retrying
* All requests can be send parallelly
* Custom startup/cleanup/callback/errback function as plugins
* Callback with request and response parameters of the most famous [requests](https://github.com/psf/requests) library

Not support yet:

* Configure proxy

* Use your own cert

* Ctrl+C quit program quickly when slow response

  

The command provides two types of options, **curl options** and **additional options**. Run ``os-pywf curl --help`` to get the full options.

**curl options** are same as the options of curl.  Usage can be found on man page of curl and help descriptions.

**additional options** enhance curl and provide additional features. 

* ``--send-timeout``, send request timeout (second), default (-1) is no timeout

* ``--receive-timeout``, receive response timeout (second), default (-1) behavior depends on some other settings such as response timeout

* ``--startup``, a function invoked when startup, before download pages. The function have only one parameter which is the series or the parallel of Workflow

* ``--cleanup``, a function invoked when cleanup, after all downdloads finish. The function have only one parameter same as startup function
  
    ```
    # app.py
    def startup(runner):
        pass

    def cleanup(runner):
        pass
    ```
    
    ```
    os-pywf curl http://www.example.com/ --startup app.startup --cleanup app.cleanup
    ```

* ``--callback``, a function invoked when response received. 
  
    We wrap PyWorkflow with most famous Python http library [requests](https://github.com/psf/requests) and provide more powerful callback. The callback function have three parameters: task, request and response.
    
    ```
    # app.py
    def callback(task, request, response):
        pass
    ```
    
    ```
    os-pywf curl http://www.example.com/ --callback app.callback
    ```
    
    * task, the PyWorkflow httptask object
    * request,  [requests.PreparedRequest](https://docs.python-requests.org/en/master/api/#requests.PreparedRequest) object, it is the original request even though there are retries and redirects
    * response, [requests.Response](https://docs.python-requests.org/en/master/api/#requests.Response) object, it is the final response when there are retries and redirects.  You can get all the response when redirect occur. If not configure errback function, the response will be ``os_pywf.exceptions.Failure`` object when transaction fail (all http response treat as success)

* ``--errback``, a function invoked when request fail. It can be ignored, all of the response and fail will invoke callback function. When provide, transaction fail will invoke this function not callback function

    ```
    # app.py
    def errback(task, request, failure):
        pass
    ```

    ```
    os-pywf curl http://www.example.com/ --errback app.errback
    ```

    * task, the PyWorkflow httptask object
    * request, same as the parameter of callback
    * Failure, ``os_pywf.exceptions.Failure`` object, it has two properties: exception and value. The value property maybe None or requests.Response depends on the fail situation
    
* ``--parallel``,  requests will be send parallelly. Attention, the framework is asynchronous, all callback/errback invoked in one thread. Block operations in one callback/errback will block the whole world

## APIs

### os_pywf.http.client



## Unit Tests

```
sh scripts/test.sh
```

## License

MIT licensed.
