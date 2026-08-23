"""Static audit of learner/evaluator process separation.

The repository's central methodological claim is that the learner never
receives evaluator-side information: target names, hidden verification
cases, or sealed benchmark metadata. ``leakage_audit`` checks the public
*contract documents* for forbidden terms, but until now nothing checked
the *code* itself. This module closes that gap with three static rules
over ``src/akgm_n0/learner``:

1. No learner module may import ``akgm_n0.evaluator``, directly or
   transitively through any chain of project modules.
2. Learner modules may import non-learner project modules only from an
   explicit shared allowlist, so new shared surface cannot appear
   without review.
3. Learner source may not contain string literals that reference sealed
   evaluator-side paths (for example ``evaluator/sealed_benchmark.yaml``),
   which would allow file-system leakage without any import.

Claim boundary: this is a static AST-level audit of the committed
source tree. It cannot detect leakage performed at runtime through
dynamic import machinery, environment variables, subprocesses, or data
files whose contents already contain target information. It restricts
the code-coupling channel; it does not by itself prove the information
boundary of any experiment.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from .contracts import PROJECT_ROOT

LEARNER_PACKAGE = "akgm_n0.learner"
EVALUATOR_PACKAGE = "akgm_n0.evaluator"
PROJECT_PACKAGE = "akgm_n0"

# Non-learner project modules the learner package is allowed to import.
# Additions to this list are shared learner/evaluator surface and must be
# reviewed for target leakage before being allowlisted.
LEARNER_SHARED_ALLOWLIST: frozenset[str] = frozenset(
    {
        "akgm_n0",
        "akgm_n0.contracts",
        "akgm_n0.leakage_audit",
    }
)

# Substrings that identify sealed evaluator-side files. A learner string
# literal containing any of these is treated as attempted path access.
SEALED_PATH_MARKERS: tuple[str, ...] = (
    "evaluator/",
    "evaluator\\",
    "sealed_benchmark",
    "leakage_policy",
)


@dataclass(frozen=True)
class IsolationFinding:
    path: str
    location: str
    kind: str
    value: str


def _discover_modules(src_root: Path) -> dict[str, Path]:
    modules: dict[str, Path] = {}
    for file_path in sorted(src_root.rglob("*.py")):
        relative = file_path.relative_to(src_root).with_suffix("")
        parts = list(relative.parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        if not parts:
            continue
        modules[".".join(parts)] = file_path
    return modules


def _package_of(module_name: str, file_path: Path) -> list[str]:
    parts = module_name.split(".")
    if file_path.name == "__init__.py":
        return parts
    return parts[:-1]


def _imported_project_modules(
    module_name: str, file_path: Path, tree: ast.Module
) -> set[str]:
    imported: set[str] = set()
    package_parts = _package_of(module_name, file_path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                base_parts = (node.module or "").split(".") if node.module else []
            else:
                anchor = package_parts[: len(package_parts) - (node.level - 1)]
                base_parts = list(anchor)
                if node.module:
                    base_parts.extend(node.module.split("."))
            base = ".".join(base_parts)
            if base:
                imported.add(base)
            for alias in node.names:
                if alias.name == "*":
                    continue
                imported.add(f"{base}.{alias.name}" if base else alias.name)
    return {name for name in imported if name.split(".")[0] == PROJECT_PACKAGE}


def _resolve_module(name: str, modules: dict[str, Path]) -> str | None:
    while name:
        if name in modules:
            return name
        if "." not in name:
            return None
        name = name.rsplit(".", 1)[0]
    return None


def _string_literals(tree: ast.Module) -> list[tuple[int, str]]:
    docstring_nodes: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                docstring_nodes.add(id(body[0].value))
    literals: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstring_nodes
        ):
            literals.append((node.lineno, node.value))
    return literals


def build_project_import_graph(
    src_root: Path | None = None,
) -> tuple[dict[str, Path], dict[str, set[str]]]:
    """Return (module map, resolved project-internal import graph)."""
    root = src_root or PROJECT_ROOT / "src"
    modules = _discover_modules(root)
    graph: dict[str, set[str]] = {}
    for module_name, file_path in modules.items():
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
        raw = _imported_project_modules(module_name, file_path, tree)
        resolved = {
            resolved_name
            for name in raw
            if (resolved_name := _resolve_module(name, modules)) is not None
        }
        graph[module_name] = resolved
    return modules, graph


def _evaluator_chain(
    start: str, graph: dict[str, set[str]]
) -> list[str] | None:
    parent: dict[str, str | None] = {start: None}
    stack = [start]
    while stack:
        current = stack.pop()
        for dependency in sorted(graph.get(current, ())):
            if dependency in parent:
                continue
            parent[dependency] = current
            if dependency.startswith(EVALUATOR_PACKAGE):
                chain = [dependency]
                while parent[chain[-1]] is not None:
                    chain.append(parent[chain[-1]])  # type: ignore[arg-type]
                chain.reverse()
                return chain
            stack.append(dependency)
    return None


def audit_learner_isolation(
    src_root: Path | None = None,
    shared_allowlist: frozenset[str] = LEARNER_SHARED_ALLOWLIST,
) -> list[IsolationFinding]:
    """Audit learner/evaluator separation; return all findings."""
    root = src_root or PROJECT_ROOT / "src"
    modules, graph = build_project_import_graph(root)
    findings: list[IsolationFinding] = []

    learner_modules = sorted(
        name
        for name in modules
        if name == LEARNER_PACKAGE or name.startswith(LEARNER_PACKAGE + ".")
    )

    for module_name in learner_modules:
        relative_path = str(modules[module_name].relative_to(root))

        for dependency in sorted(graph[module_name]):
            in_learner = dependency == LEARNER_PACKAGE or dependency.startswith(
                LEARNER_PACKAGE + "."
            )
            if dependency.startswith(EVALUATOR_PACKAGE):
                findings.append(
                    IsolationFinding(
                        relative_path,
                        module_name,
                        "direct_evaluator_import",
                        dependency,
                    )
                )
            elif not in_learner and dependency not in shared_allowlist:
                findings.append(
                    IsolationFinding(
                        relative_path,
                        module_name,
                        "shared_module_not_allowlisted",
                        dependency,
                    )
                )

        chain = _evaluator_chain(module_name, graph)
        if chain is not None and len(chain) > 2:
            findings.append(
                IsolationFinding(
                    relative_path,
                    module_name,
                    "transitive_evaluator_import",
                    " <- ".join(reversed(chain)),
                )
            )

        tree = ast.parse(modules[module_name].read_text(encoding="utf-8"))
        for lineno, value in _string_literals(tree):
            lowered = value.casefold()
            for marker in SEALED_PATH_MARKERS:
                if marker in lowered:
                    findings.append(
                        IsolationFinding(
                            relative_path,
                            f"{module_name}:{lineno}",
                            "sealed_path_reference",
                            value,
                        )
                    )
                    break

    return findings
