# type: ignore[attr-defined]
"""Python API for acquisition and control of Edinburgh Sensors Gascard."""

import sys
from importlib import metadata as importlib_metadata


def get_version() -> str:
    """Get the version of the package.

    Returns:
        str: The version of the package.
    """
    try:
        return importlib_metadata.version(__name__)
    except importlib_metadata.PackageNotFoundError:  # pragma: no cover
        return "unknown"


version: str = get_version()
