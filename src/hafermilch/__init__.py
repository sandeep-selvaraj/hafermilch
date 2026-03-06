from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("hafermilch")
except PackageNotFoundError:
    __version__ = "dev"
