from __future__ import annotations

import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.isolation_audit import (
    LEARNER_SHARED_ALLOWLIST,
    audit_learner_isolation,
    build_project_import_graph,
)


def _write(root: Path, relative: str, source: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(source), encoding="utf-8")


def _make_minimal_tree(root: Path) -> None:
    _write(root, "akgm_n0/__init__.py", "")
    _write(root, "akgm_n0/contracts.py", "VALUE = 1\n")
    _write(root, "akgm_n0/learner/__init__.py", "")
    _write(root, "akgm_n0/evaluator/__init__.py", "")
    _write(root, "akgm_n0/evaluator/hidden_cases.py", "SECRET = 'target'\n")


class RepositoryIsolationTests(unittest.TestCase):
    def test_repository_learner_is_isolated_from_evaluator(self) -> None:
        findings = audit_learner_isolation()
        self.assertEqual(
            [],
            findings,
            "Learner/evaluator separation violated:\n"
            + "\n".join(
                f"{f.path} {f.location}: {f.kind}={f.value!r}" for f in findings
            ),
        )

    def test_repository_learner_package_is_nonempty(self) -> None:
        modules, _graph = build_project_import_graph()
        learner = [m for m in modules if m.startswith("akgm_n0.learner")]
        self.assertGreater(
            len(learner),
            1,
            "Audit must actually see learner modules; an empty scope "
            "would pass vacuously.",
        )


class DetectionTests(unittest.TestCase):
    def _audit(self, root: Path):
        return audit_learner_isolation(src_root=root)

    def test_detects_direct_evaluator_import(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_minimal_tree(root)
            _write(
                root,
                "akgm_n0/learner/cheater.py",
                """
                from akgm_n0.evaluator.hidden_cases import SECRET
                """,
            )
            kinds = {f.kind for f in self._audit(root)}
            self.assertIn("direct_evaluator_import", kinds)

    def test_detects_relative_evaluator_import(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_minimal_tree(root)
            _write(
                root,
                "akgm_n0/learner/cheater.py",
                """
                from ..evaluator import hidden_cases
                """,
            )
            kinds = {f.kind for f in self._audit(root)}
            self.assertIn("direct_evaluator_import", kinds)

    def test_detects_transitive_evaluator_import(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_minimal_tree(root)
            _write(
                root,
                "akgm_n0/bridge.py",
                """
                from akgm_n0.evaluator import hidden_cases
                """,
            )
            _write(
                root,
                "akgm_n0/learner/indirect.py",
                """
                from akgm_n0 import bridge
                """,
            )
            findings = self._audit(root)
            kinds = {f.kind for f in findings}
            self.assertIn("transitive_evaluator_import", kinds)
            chains = [
                f.value
                for f in findings
                if f.kind == "transitive_evaluator_import"
            ]
            self.assertTrue(
                any("akgm_n0.bridge" in chain for chain in chains),
                f"Chain should name the bridge module: {chains}",
            )

    def test_detects_non_allowlisted_shared_module(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_minimal_tree(root)
            _write(root, "akgm_n0/new_shared.py", "VALUE = 2\n")
            _write(
                root,
                "akgm_n0/learner/uses_shared.py",
                """
                from akgm_n0.new_shared import VALUE
                """,
            )
            kinds = {f.kind for f in self._audit(root)}
            self.assertIn("shared_module_not_allowlisted", kinds)

    def test_allowlisted_shared_module_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_minimal_tree(root)
            _write(
                root,
                "akgm_n0/learner/uses_contracts.py",
                """
                from akgm_n0.contracts import VALUE
                """,
            )
            self.assertEqual([], self._audit(root))

    def test_detects_sealed_path_string_literal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_minimal_tree(root)
            _write(
                root,
                "akgm_n0/learner/reads_sealed.py",
                """
                PATH = "evaluator/sealed_benchmark.yaml"
                """,
            )
            kinds = {f.kind for f in self._audit(root)}
            self.assertIn("sealed_path_reference", kinds)

    def test_docstring_mentioning_evaluator_is_not_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_minimal_tree(root)
            _write(
                root,
                "akgm_n0/learner/documented.py",
                '''
                """Interpretations live in the evaluator/ directory."""

                VALUE = 3
                ''',
            )
            self.assertEqual([], self._audit(root))

    def test_learner_internal_imports_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_minimal_tree(root)
            _write(root, "akgm_n0/learner/helper.py", "VALUE = 4\n")
            _write(
                root,
                "akgm_n0/learner/main.py",
                """
                from .helper import VALUE
                from akgm_n0.learner import helper
                """,
            )
            self.assertEqual([], self._audit(root))


class AllowlistDocumentationTests(unittest.TestCase):
    def test_allowlist_modules_exist_in_repository(self) -> None:
        modules, _graph = build_project_import_graph()
        for name in LEARNER_SHARED_ALLOWLIST:
            self.assertIn(
                name,
                modules,
                f"Allowlisted shared module {name!r} does not exist; "
                "remove stale entries so the allowlist stays reviewable.",
            )

    def test_allowlisted_modules_do_not_import_evaluator(self) -> None:
        _modules, graph = build_project_import_graph()
        for name in LEARNER_SHARED_ALLOWLIST:
            for dependency in graph.get(name, ()):
                self.assertFalse(
                    dependency.startswith("akgm_n0.evaluator"),
                    f"Shared module {name!r} imports evaluator module "
                    f"{dependency!r}, which would leak through the "
                    "allowlist.",
                )


if __name__ == "__main__":
    unittest.main()
