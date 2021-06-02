try:
    from importlib.metadata import metadata, version  # type: ignore
except ModuleNotFoundError:
    from importlib_metadata import metadata, version  # type: ignore

__version__ = version('hodlclaim')
__doc__ = metadata('hodlclaim')['Summary']
__author__ = metadata('hodlclaim')['Author']

from .claim import *
