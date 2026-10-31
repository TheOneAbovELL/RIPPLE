"""Smoke test: the package imports and reports a version."""

import ripple


def test_smoke_imports_ripple_package():
    assert ripple.__version__ == "0.0.1"
