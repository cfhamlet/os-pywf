# os-pywf

[![Build Status](https://www.travis-ci.org/cfhamlet/os-pywf.svg?branch=master)](https://www.travis-ci.org/cfhamlet/os-pywf)
[![codecov](https://codecov.io/gh/cfhamlet/os-pywf/branch/master/graph/badge.svg)](https://codecov.io/gh/cfhamlet/os-pywf)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/os-pywf.svg)](https://pypi.python.org/pypi/os-pywf)
[![PyPI](https://img.shields.io/pypi/v/os-pywf.svg)](https://pypi.python.org/pypi/os-pywf)

[Workflow](https://github.com/sogou/workflow) and [PyWorkflow](https://github.com/sogou/pyworkflow)(Python binding of Workflow) are great async frameworks.

This project is tryig to explore the power of Workflow. We provide high level APIs and command line tools for convenient.

## Install

```
pip install os-pywf
```


## Command line

``os-pywf`` command can be used after installation.

```
$ os-pywf
Usage: os-pywf [OPTIONS] COMMAND [ARGS]...

  Command line tool for os-pywf.

Options:
  --version                      Show the version and exit.
  --compute-threads INTEGER      Number of compute threads.  [default: 4]
  --handler-threads INTEGER      Number of handler threads.  [default: 4]
  --poller-threads INTEGER       Number of poller threads.  [default: 4]
  --dns-threads INTEGER          Number of dns threads.  [default: 4]
  --dns-ttl-default INTEGER      Default seconds of dns ttl.  [default: 43200]
  --dns-ttl-min INTEGER          Min seconds of dns ttl.  [default: 180]
  --max-connections INTEGER      Max number of connections.  [default: 200]
  --connection-timeout INTEGER   Connect timeout.  [default: 10000]
  --response-timeout INTEGER     Response timeout.  [default: 10000]
  --ssl-connect-timeout INTEGER  SSL connect timeout.  [default: 10000]
  --help                         Show this message and exit.

Commands:
  http   HTTP tools.
```

Global settings of Workflow can be specified with options, ENVs is not supported yet.


### Subcommand introductions:

You can get help information of subcommands with ``--help`` option

* ``http client``
    * most options are same as curl, so the command options line can also be used with curl
    * more than one request can be send, just specify multiple URLs
    * extra options which curl not supported:
        * ``--callback``, once set to an importable python function path, the function will be called when response arrived or request fail
        * ``--retry``, retry times when request fail
        * ``--parallel``, send requests parallelly


## APIs

[TODO]

## Unit Tests

```
sh scripts/test.sh
```

## License

MIT licensed.
