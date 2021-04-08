import pathlib

import os_pywf


def test_version():
    version_file = (
        pathlib.Path(__file__).parents[1].joinpath("src/os_pywf/VERSION").absolute()
    )
    assert os_pywf.__version__ == open(version_file).read().strip()


if __name__ == "__main__":
    test_version()
