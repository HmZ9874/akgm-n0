import unittest

from akgm_n0.evaluator.self_extending_substrate_v15 import run_v15_acceptance
from akgm_n0.learner.self_extending_substrate_v15 import (
    VM_OPS,
    CrossTaskMacroMinerV15,
    UnifiedCounterVM,
    default_anonymous_tasks,
    migrated_training_programs,
    primitive_leakage_audit,
    rename_registers,
)


class SelfExtendingSubstrateV15Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.programs = migrated_training_programs()
        cls.tasks = default_anonymous_tasks()
        cls.acceptance = run_v15_acceptance()

    def test_one_primitive_vm_replays_all_three_memories(self):
        vm = UnifiedCounterVM()
        for task_id, program in self.programs.items():
            self.assertTrue(all(vm.execute(program, inputs).outputs == expected for inputs, expected in self.tasks[task_id].cases))
            self.assertTrue({item.op for item in program.instructions}.issubset(VM_OPS))

    def test_register_renaming_preserves_semantics(self):
        vm = UnifiedCounterVM()
        for task_id, program in self.programs.items():
            renamed = rename_registers(program, tuple(reversed(range(program.register_count))))
            self.assertTrue(all(vm.execute(renamed, inputs).outputs == expected for inputs, expected in self.tasks[task_id].cases))

    def test_cross_task_macro_is_real_and_compressive(self):
        macros = CrossTaskMacroMinerV15().mine(self.programs)
        self.assertTrue(macros)
        self.assertGreaterEqual(macros[0].task_support, 3)
        self.assertGreater(macros[0].savings_per_use, 0)

    def test_program_surface_has_no_named_arithmetic_opcode(self):
        self.assertTrue(primitive_leakage_audit(self.programs.values())["passed"])

    def test_full_acceptance_and_efficiency_gate(self):
        self.assertTrue(self.acceptance["passed"])
        self.assertGreaterEqual(self.acceptance["aggregate"]["evaluation_reduction"], 0.8)
        self.assertTrue(all(item["converged"] for item in self.acceptance["reconstructions"]))
        self.assertFalse(self.acceptance["proposal_policy"]["transformer"])


if __name__ == "__main__":
    unittest.main()
