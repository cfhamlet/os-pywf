# os-pywf

[![Build Status](https://www.travis-ci.org/cfhamlet/os-pywf.svg?branch=master)](https://www.travis-ci.org/cfhamlet/os-pywf)
[![codecov](https://codecov.io/gh/cfhamlet/os-pywf/branch/master/graph/badge.svg)](https://codecov.io/gh/cfhamlet/os-pywf)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/os-pywf.svg)](https://pypi.python.org/pypi/os-pywf)
[![PyPI](https://img.shields.io/pypi/v/os-pywf.svg)](https://pypi.python.org/pypi/os-pywf)

[Workflow](https://github.com/sogou/workflow) and [PyWorkflow](https://github.com/sogou/pyworkflow)(Python binding of Workflow) are great async frameworks.

This project is trying to explore the power of the framework and provide command line tools and high level APIs for convenient.

## Install

```
pip install os-pywf
```


## Command line

``os-pywf`` command can be used after installation. There are several command line tools can be used. You can get help information of subcommands with ``--help`` option.  Global settings of Workflow can be specified, ENVs is not supported yet.

The commands with *planning* tag will be developed later, can not be used right now.

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

This sub-command is inspired by curl. It works as curl and provides more powerful features especially invoke Python function as response process callback from command line, which make this command flexible and easy to use.

The command provides two types of options, curl options and additional options.


## APIs

### os_pywf.http.client



## Unit Tests

```
sh scripts/test.sh
```

## License

MIT licensed.
