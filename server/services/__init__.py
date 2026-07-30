"""Application service layer — the only path from web routes into core/.

Routes must never import core.token_store / core.sheet_runner directly:
that is how a second, divergent publishing implementation starts (ADR-003).
"""
