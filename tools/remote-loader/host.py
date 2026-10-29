#!/usr/bin/env python3
"""Compatibility entry point; the shared host lives in tools/host.py."""
import os
import runpy

if __name__ == "__main__":
    runpy.run_path(os.path.join(os.path.dirname(__file__), "..", "host.py"), run_name="__main__")
