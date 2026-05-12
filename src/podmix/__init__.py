"""podmix: podcast voice + BGM + outro auto-mixer."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("podmix")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"
