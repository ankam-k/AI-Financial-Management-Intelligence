"""Pydantic request/response models — the API's contract with the client.

Kept separate from the ORM models on purpose. They answer different
questions: an ORM model describes what is stored, a schema describes what is
accepted and shown. Collapsing them means every column rename is a breaking
API change and every internal field is public by default.
"""
