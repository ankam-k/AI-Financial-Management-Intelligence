"""Service layer — where the business rules live.

A service takes a ``Session`` and a ``Clock`` and knows nothing about HTTP.
Routers translate requests into service calls and service results into
responses; they contain no rules of their own. That split is what makes the
rules testable without a web server and reusable from a future CLI seeder or
background analysis job.

V1 skips the repository interfaces that ADR-001 specifies. With one database
and no second adapter in sight, a repository port would be an indirection
whose only implementation is the one it hides (ADR-014). The seam that
matters — services never import FastAPI — is preserved.
"""
