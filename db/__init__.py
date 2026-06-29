"""Additive Supabase layer. NOT a dependency of the graded path.

core/ never imports this. Every call here is best-effort: if Supabase is
unconfigured or unreachable, functions log a warning and return None — the
orders_log.txt write (core/persistence.py) remains the primary, mandatory output.
"""
