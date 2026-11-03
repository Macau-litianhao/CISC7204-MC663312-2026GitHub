"""team01 - analysis package for the CISC7204 Team 01 semester project.

Import order inside the package is deliberately flat: ``schema`` holds constants
only, ``config`` holds settings only, and every other module imports from one or
both. Nothing here imports pandas at package-import time, so ``import team01``
stays cheap for the test suite and the Dash app.
"""

from __future__ import annotations

__version__ = "0.2.0"
__all__ = ["__version__"]
