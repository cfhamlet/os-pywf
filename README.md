# os-pywf

[![Build Status](https://www.travis-ci.org/cfhamlet/os-pywf.svg?branch=main)](https://www.travis-ci.org/cfhamlet/os-pywf)
[![codecov](https://codecov.io/gh/cfhamlet/os-pywf/branch/main/graph/badge.svg)](https://codecov.io/gh/cfhamlet/os-pywf)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/os-pywf.svg)](https://pypi.python.org/pypi/os-pywf)
[![PyPI](https://img.shields.io/pypi/v/os-pywf.svg)](https://pypi.python.org/pypi/os-pywf)

[Workflow](https://github.com/sogou/workflow) and it's Python binding [PyWorkflow](https://github.com/sogou/pyworkflow) are great async frameworks.

This project is trying to explore the power of Workflow, provide command line tools and high level APIs for real world development.

## Install

```
pip install os-pywf
```


## Commands

``os-pywf`` command can be used after installation. You can get help information with ``--help`` option.  Global settings of Workflow can be specified, ENVs is not supported yet.

The subcommands with *planning* tag will be developed later, can not be used right now.

```
$ os-pywf --help
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
  curl    HTTP client inspired by curl (beta).
  mysql   MySQL client (planning).
  proxy   HTTP proxy (planning).
  redis   Redis client (planning).
  run     Run runnable objects of pywf (planning).
  spider  Web spider (planning).
  web     Web server (planning).
```



### curl

This subcommand is inspired by curl. It works as curl and provides more useful features especially invoke Python function as response callback, which make it flexible and easy to extend.

```
$ os-pywf curl --help
Usage: os-pywf curl [OPTIONS] [URLS]...

  HTTP client inspired by curl (beta).

Options:
  Curl options:                   Options same as curl.
    -0, --http1.0                 Use HTTP 1.0
    -A, --user-agent TEXT         User-Agent to send to server.  [default: os-
                                  pywf/0.0.1]

    -b, --cookie TEXT             String or file to read cookies from.
    -c, --cookie-jar FILENAME     Write cookies to this file after operation.
    -d, --data TEXT               HTTP POST data.
    --data-urlencode TEXT         HTTP POST data url encoded.
    -e, --referer TEXT            Referer URL.
    -F, --form TEXT               Specify HTTP multipart POST data.
    -H, --header TEXT             Custom header to pass to server.
    -L, --location                Follow redirects.
    --max-filesize INTEGER        Maximum data size (in bytes) to download.
    --max-redirs INTEGER          Maximum number of redirects allowed.
                                  [default: 30]

    -u, --user TEXT               Specify the user name and password to use
                                  for  server  authentication.

    --no-keepalive                Disable keepalive.
    --retry INTEGER               Maximum retries when request fail.
                                  [default: 0]

    --retry-delay FLOAT           Time between two retries(s).  [default: 0]
    -x, --proxy TEXT              Specify proxy.
    -X, --request [DELETE|GET|HEAD|OPTIONS|PATCH|POST|PUT]
                                  Request method. [default: GET]
  Additional options:             Additional options.
    --send-timeout FLOAT          Send request timeout(s).  [default: -1]
    --receive-timeout FLOAT       Receive response timeout(s).  [default: -1]
    --startup TEXT                Function invoked when startup.  [default:
                                  os_pywf.commands.curl.startup]

    --cleanup TEXT                Function invoked when cleanup.  [default:
                                  os_pywf.commands.curl.cleanup]

    --callback TEXT               Function invoked when response received.
                                  [default: os_pywf.commands.curl.callback]

    --errback TEXT                Function invoked when request fail (callback
                                  will be invoked when no errback).

    --parallel                    Send requests parallelly.
    --log-level [CRITICAL|ERROR|WARNING|INFO|DEBUG]
                                  Log level.  [default: INFO]
    --debug                       Enable debug mode.
  --help                          Show this message and exit.
```



Example:

```
# app.py
def callback(task, request, response):
    print(request, response)
```

```
os-pywf curl http://www.example.com/ --callback app.callback
```



Features:

* Same options as curl, command line can be used by curl directly
* Support HTTP version 1.0/1.1 
* Auto manipulate cookies. Cookies can be specified by command line or read from file. Cookies can be saved to file
* Support post urlencode data
* Support upload files as multipart form
* Support redirect. Response history can be accessed with [response.history](https://docs.python-requests.org/en/master/api/#requests.Response.history)
* Support retry and retry interval.  The program can be quickly canceled when retrying
* All requests can be send parallelly (async not multithread)
* Custom startup/cleanup/callback/errback function as plugins
* Callback with request and response parameters of the most famous [Requests](https://github.com/psf/requests) library
* Support auto decompress response data (v0.0.2)
* Support set proxy for http (not https) request (v0.0.3)
* Generate requests from callback and download continuously (v0.0.4)

Issues/Not support:

* Configure proxy
* Use your own cert
* Ctrl+C to quit program slowly when downloading slow response

  

The command provides two types of options, **curl options** and **additional options**. Run ``os-pywf curl --help`` to get the full help information.

**curl options** are same as the options of curl.  Usage can be found on man page of curl and help descriptions.

**additional options** enhance curl and provide additional features. 

* ``--send-timeout``, send request timeout (second), default (-1) is no timeout

* ``--receive-timeout``, receive response timeout (second), default (-1) behavior depends on some other settings such as response timeout

* ``--startup``, a function invoked when startup, before download pages. The function have only one parameter which is the series or the parallel of Workflow

* ``--cleanup``, a function invoked when cleanup, after all downloads finish. The function have only one parameter same as startup function
  
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

* ``--callback``,  ``--errback`` functions invoked when response received or fail, see [more details](#callbackerrback)
  
* ``--parallel``,  requests will be send parallelly. Attention, the framework is asynchronous, all callback/errback invoked in one thread. Block operations in callback/errback will block the whole world

## APIs

### os_pywf.http.client

This module provides hight level HTTP client APIs. Inspired by the most famous Python HTTP library [Requests](https://github.com/psf/requests), the APIs are nearly the same.

All of the request APIs do not send request and block wait response, they all return HttpTask object for Workflow and invoke callback function when response downloaded.

We wrap the PyWorkflow HttpTask and provide more convenient callback with [request](https://docs.python-requests.org/en/master/api/#requests.PreparedRequest) and [response](https://docs.python-requests.org/en/master/api/#requests.Response) as additional parameters, they all typical instance of Requests library as you know.

```
import pywf
from os_pywf.http import client

def callback(task, request, response):
    print(request, response)

task = client.get("http://www.example.com/", callback=callback)
task.start()
pywf.wait_finish()
```

We provide more useful features which PyWorkflow not support directly:

* session with cookies persistence
* redirect responses history
* retry interval and quick cancel
* authentication
* post urlencode data and multipart files upload
* auto decompress response data (v0.0.2)
* set proxy for http (not https) request (v0.0.3)

You can use Session to configure same settings of  a group tasks, it also auto manipulate cookies and provide cancel function to cancel all tasks create by the same session. You can create Session as normal class or as a context manager:

```
import pywf
from os_pywf.http import client
from os_pywf.utils import create_series_work

def callback(task, request, response):
    print(request, response)
    
series = create_series_work()
headers = {"User-Agent": "os-pywf/beta"}
with client.Session(headers=headers, callback=callback) as session:
    for url in ["http://www.example.com/", "http://httpbin.org/"]:
        task = session.get(url)
        series.push_back(task)
series.start()
pywf.wait_finish()
```

Session can be canceled, when canceled the tasks created by the session which not started  will be destroyed, running task will still run until finish but callback will not invoked. 

```
...
# register cancel for Ctrl+C 
with client.Session() as session:
    def _cancel(signum, frame):    
        session.cancel()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, _cancel)
...
```

#### callback/errback

For callback async type of Workflow, we provide two functions as request/session parameters for framework: callback and errback

We wrap PyWorkflow with most famous Python HTTP library [Requests](https://github.com/psf/requests) and provide more powerful callback and errback

* **callback**, invoked when response received,  three parameters: task, request, response
  
    ```
    def callback(task, request, response):
        pass
    ```
    * **task**, the PyWorkflow HttpTask object
    * **request**,  [requests.PreparedRequest](https://docs.python-requests.org/en/master/api/#requests.PreparedRequest) object, it is the original request even though there are retries and redirects
    * **response**, [requests.Response](https://docs.python-requests.org/en/master/api/#requests.Response) object, it is the final response when there are retries and redirects.  You can get all the response when redirect occur. If not set errback function, the response will be ``os_pywf.exceptions.Failure`` object when transaction fail (all HTTP response treat as success)
    
* **errback**, invoked when transaction fail. It can be ignored, all of the response and fail will invoke callback function, three parameters: task, request, failure

    ```
    def errback(task, request, failure):
        pass
    ```
    
    * **task**, the PyWorkflow HttpTask object
    * **request**, same as the parameter of callback
    * **Failure**, ``os_pywf.exceptions.Failure`` object, it has two properties: exception and value. The value property maybe None or [requests.Response](https://docs.python-requests.org/en/master/api/#requests.Response) depends on the fail situation
    
* both callback and errback can have return value (from v0.0.4) for framework to schedule. There are several types object can be returned

    * ``str``，must be URL，it will be wrapped with session as HttpTask and add to the head of the series 
    * ``requests.Request``, it will be wrapped with session as HttpTask and add to the head of the series
    * ``requests.PreparedRequest``, it will be wrapped **without** session as HttpTask and add to the head of the series
    * ``pywf.SubTask``, it will be add to the head of the series
    * ``list``, the elements will be treated as above object add to the head of the series from last to first
    * ``tuple``, first element treated as above object, second element will add to the tail of the series 

### os_pywf.utils

* **create_series_work**, wrap the create_series_work of PyWorkflow, you can pass arbitrary tasks to create series.

* **create_timer_task**, wrap the create_timer_task of PyWorkflow. It split the wait time into small time pieces, so it can be canceled as soon as possible.

  You can pass a threading.Event object as cancel parameter.


### os_pywf.exceptions

* **Failure**, failure for usually for errback, two properties: exception and value. The real value object depend on fail situation
* **WFException**, exception about task fail,  two properties: state and code. state come from ``task.get_state()``, code come from ``task.get_error()``. You can get human readable error string by  use built-in str function.

## Unit Tests

```
sh scripts/test.sh
```

## License

MIT licensed.
