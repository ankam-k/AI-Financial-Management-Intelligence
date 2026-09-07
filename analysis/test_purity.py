"""The analysis engine's import boundary.

ADR-001 makes the engine's inability to reach a database or a model a
*structural* property rather than a convention — "it is structurally incapable
of calling a model" is the claim, and a claim like that has to be checked by
something other than reviewer attention.

The approved architecture enforces this with an import-linter in CI. V1 has no
CI (ADR-014), so the same guarantee is asserted here: a build fails the moment
``app/analysis/`` imports a database driver, a web framework, or an HTTP
client.

Parsing the AST rather than importing the modules is deliberate — an import
check performed by importing would be satisfied by any module that manages to
import successfully, which is exactly the thing under test.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2] / "backend"
ANALYSIS_PACKAGE = BACKEND / "app" / "analysis"

#: The narration layer is held to the same rule, for the same reason. It
#: converts finished insights into prose and must never be able to fetch more
#: data — "the AI must never read directly from the database" is a property of
#: the import graph here, not a instruction anyone has to remember. The model
#: client is injected through a protocol; the adapters that do network I/O
#: live in ``app/llm/`` and are not imported here.
NARRATION_PACKAGE = BACKEND / "app" / "narration"

#: Anything that would let the engine perform I/O, call a model, or depend on
#: the transport it happens to be served over.
FORBIDDEN_ROOTS = frozenset(
    {
        "sqlalchemy",
        "fastapi",
        "starlette",
        "pydantic",
        "httpx",
        "requests",
        "urllib",
        "socket",
        "sqlite3",
        "subprocess",
        "openai",
        "anthropic",
        "ollama",
        "os",
        "pathlib",
        "shutil",
    }
)

#: Modules inside `app` that the engine may depend on. Everything else in the
#: application depends on the engine, not the other way round.
ALLOWED_APP_MODULES = frozenset({"app.analysis", "app.domain"})

#: Narration may additionally read finished insights and the model *protocol*
#: — but never a concrete adapter, which is what keeps the network out.
ALLOWED_NARRATION_MODULES = ALLOWED_APP_MODULES | {"app.narration", "app.llm.base"}


def analysis_modules() -> list[Path]:
    return sorted(ANALYSIS_PACKAGE.rglob("*.py"))


def narration_modules() -> list[Path]:
    return sorted(NARRATION_PACKAGE.rglob("*.py"))


def imported_roots(path: Path) -> set[str]:
    """Top-level module names imported by a file, from its AST."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module)
    return roots


def test_the_package_was_found() -> None:
    """Guards the test itself: a wrong path would make every check below
    vacuously pass."""
    assert ANALYSIS_PACKAGE.is_dir()
    assert len(analysis_modules()) >= 9


@pytest.mark.parametrize("module", analysis_modules(), ids=lambda p: p.name)
def test_the_engine_imports_no_io_capable_library(module: Path) -> None:
    offenders = {
        name
        for name in imported_roots(module)
        if name.split(".")[0] in FORBIDDEN_ROOTS
    }

    assert offenders == set(), (
        f"{module.name} imports {sorted(offenders)}. The analysis engine must "
        "stay incapable of I/O (ADR-001) — load data in "
        "app/services/analysis_service.py and pass it in as a dataset."
    )


@pytest.mark.parametrize("module", analysis_modules(), ids=lambda p: p.name)
def test_the_engine_depends_only_on_itself_and_the_domain(module: Path) -> None:
    app_imports = {
        name for name in imported_roots(module) if name.split(".")[0] == "app"
    }
    offenders = {
        name
        for name in app_imports
        if not any(name.startswith(allowed) for allowed in ALLOWED_APP_MODULES)
    }

    assert offenders == set(), (
        f"{module.name} imports {sorted(offenders)}. The dependency arrow runs "
        "towards the engine, never out of it."
    )


def test_the_narration_package_was_found() -> None:
    assert NARRATION_PACKAGE.is_dir()
    assert len(narration_modules()) >= 6


@pytest.mark.parametrize("module", narration_modules(), ids=lambda p: p.name)
def test_narration_imports_no_io_capable_library(module: Path) -> None:
    offenders = {
        name for name in imported_roots(module) if name.split(".")[0] in FORBIDDEN_ROOTS
    }

    assert offenders == set(), (
        f"{module.name} imports {sorted(offenders)}. The narration layer must stay "
        "incapable of fetching its own data — it explains a finished insight and "
        "nothing else."
    )


@pytest.mark.parametrize("module", narration_modules(), ids=lambda p: p.name)
def test_narration_never_imports_a_concrete_model_adapter(module: Path) -> None:
    """The client arrives through the ``LLMClient`` protocol.

    Importing ``app.llm.ollama`` here would put a socket one call away from the
    prompt builder and make the validators untestable without a server.
    """
    app_imports = {name for name in imported_roots(module) if name.split(".")[0] == "app"}
    offenders = {
        name
        for name in app_imports
        if not any(name.startswith(allowed) for allowed in ALLOWED_NARRATION_MODULES)
    }

    assert offenders == set(), (
        f"{module.name} imports {sorted(offenders)}. Narration may depend on the "
        "model protocol, never on an adapter that opens a connection."
    )
