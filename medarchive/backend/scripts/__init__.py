"""Operational scripts: load_reference, generate_reference, generate_fixtures, ingest, evaluate_matching.

Importing the package forces UTF-8 console output on Windows so Cyrillic/Kazakh
service names (and arrows/checkmarks) don't crash on the cp1251 default codepage.
"""
import sys as _sys

if _sys.platform == "win32":
    for _stream in (_sys.stdout, _sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
