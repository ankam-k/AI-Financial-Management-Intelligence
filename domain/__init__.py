"""Pure domain layer: enums, value helpers, errors.

Nothing here imports FastAPI, SQLAlchemy, or any I/O library. That constraint
is what ADR-001 protects with an import-linter in CI; in V1 it is protected by
review and by this docstring.
"""
