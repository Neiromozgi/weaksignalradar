"""Baseline pytest-discoverable test for the A-02 quality gate.

This intentionally only checks that the package is installed and importable
with the expected version; it does not exercise any product logic, since no
discovery/verification/ranking functionality is authorized for Stage A yet.
"""

from weaksignalradar import __version__


def test_package_is_importable_with_expected_version() -> None:
    assert isinstance(__version__, str)
    assert __version__ == "0.1.0"
