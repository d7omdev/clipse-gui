#!/usr/bin/env python3
"""Dev entry shim for in-tree runs.

The canonical entry point is `clipse_gui.cli:main`, exposed as `clipse-gui`
via `[project.scripts]` once installed from the wheel. This file just lets
`python clipse-gui.py` work from a fresh checkout.
"""

import os
import sys

# Make the package importable when running from source without installing.
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

from clipse_gui.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
