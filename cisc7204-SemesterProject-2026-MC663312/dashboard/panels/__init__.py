"""Figure builders, one module per panel.

Each module owns exactly one panel so that a change to one chart cannot move
another. Shared colour, type and margin tokens live in ``theme``; nothing here
hard-codes a hex value.

Import the builders from their module (``from panels.cause import cause_figure``)
rather than through this package: keeping this file empty of re-exports is what
lets two people edit two panels at the same time without touching one shared
file.
"""
