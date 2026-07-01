"""Stage 3 conversational AI layer (chat + voice).

Orchestration only — all business logic stays in core/ and is reached via the
tool executor in ai/tools.py. This package may import core/ and db/, but core/
never imports ai/, so the graded ordering path runs without any of this.
"""
