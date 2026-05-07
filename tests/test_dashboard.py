import importlib


def test_dashboard_module_imports_with_optional_geo_missing():
    importlib.import_module("src.dashboard.app")
