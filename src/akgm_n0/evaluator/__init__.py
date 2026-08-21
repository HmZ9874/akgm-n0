"""Evaluator-only environment and benchmark components."""

from .environment import (
    HiddenIntegerGridEnvironment,
    HiddenSymbolTraceEnvironment,
    HiddenSequenceEnvironment,
    SequenceWorldSpec,
)
from .ledger import KnowledgeLedger, KnowledgeState, LedgerError
from .formula_room import (
    FormulaRoomError,
    FormulaSuccessRoom,
    SuccessfulFormulaRecord,
)
from .mistakes import (
    MistakeLibrary,
    MistakeLibraryError,
    MistakeRecord,
    program_family_signature,
)
from .relation_mistakes import (
    RelationMistakeLibrary,
    RelationMistakeLibraryError,
    RelationMistakeRecord,
    relation_semantic_signature,
)
from .micro_mistakes import (
    MicroMistakeLibrary,
    MicroMistakeLibraryError,
    MicroMistakeRecord,
)
from .indexed_mistakes import (
    IndexedMistakeLibrary,
    IndexedMistakeLibraryError,
    IndexedMistakeRecord,
)
from .adaptive_mistakes import (
    AdaptiveMistakeLibrary,
    AdaptiveMistakeLibraryError,
    AdaptiveMistakeRecord,
)
from .verifier import IndependentVerifier, VerificationCase, VerificationReport
from .universal_proof import (
    DOMAIN_NATURAL,
    DOMAIN_NATURAL_PAIRS,
    DOMAIN_NATURAL_POSITIVE_DIVISOR,
    ProvenFormulaRecord,
    UniversalFormulaCertificate,
    UniversalFormulaRoom,
    UniversalProofError,
    UniversalProofVerification,
    UniversalProofVerifier,
    program_digest,
)
from .state_window_semantic_proof import verify_state_window_semantic
from .micro_operator_proof import verify_micro_operator, verify_micro_operator_batch
from .semantic_room import SemanticRoomError, VerifiedSemanticRoom
from .evolved_operator_proof import (
    verify_evolved_operator,
    verify_evolved_operator_batch,
)
from .evolved_semantic_room import (
    EvolvedSemanticRoomError,
    VerifiedEvolvedSemanticRoom,
)
from .universal_semantic_audit import (
    UniversalSemanticAudit,
    UniversalSemanticAuditor,
    UniversalSemanticAuditLoop,
)
from .guarded_reduction_proof import verify_guarded_reduction_semantic
from .continuous_semantic_proof import verify_continuous_semantics
from .repeat_macro_proof import verify_repeat_macro_semantic
from .mass_formula_proof import (
    FIRST_OPCODE as MASS_FORMULA_FIRST_OPCODE,
    FORMULA_COUNT as MASS_FORMULA_COUNT,
    formula_id,
    semantic_normal_form,
    structural_logic_signature as mass_formula_logic_signature,
    verify_mass_formula_batch,
)
from .formula_rejection_room import FormulaRejectionRoom
from .foundation_proof import verify_foundation_semantic
from .foundation_room import FoundationSemanticRoom
from .reversible_foundation_proof import verify_reversible_foundation_semantic
from .reversible_foundation_room import ReversibleFoundationRoom
from .directional_foundation_proof import verify_directional_foundation_semantic
from .directional_foundation_room import DirectionalFoundationRoom
from .nested_foundation_proof import (
    verify_nested_foundation_semantic,
    verify_partition_foundation_semantic,
)
from .nested_foundation_room import NestedFoundationRoom, PartitionFoundationRoom
from .autonomous_frontier_proof import verify_recursive_foundation_semantic
from .autonomous_frontier_room import AutonomousFrontierRoom
from .distinct_frontier_proof import verify_distinct_foundation_semantic
from .distinct_frontier_room import DistinctFrontierRoom
from .canonical_frontier_proof import verify_canonical_foundation_semantic
from .canonical_frontier_room import CanonicalFrontierRoom
from .ratio_frontier_proof import verify_ratio_foundation_semantic
from .ratio_frontier_room import RatioFrontierRoom
from .finite_mass_proof import verify_finite_mass_semantic
from .finite_mass_room import FiniteMassRoom
from .joint_frontier_proof import verify_joint_foundation_semantic
from .joint_frontier_room import JointFrontierRoom
from .weighted_frontier_proof import verify_weighted_foundation_semantic
from .weighted_frontier_room import WeightedFrontierRoom
from .rational_algebra_proof import verify_rational_algebra_semantic
from .rational_algebra_room import RationalAlgebraRoom
from .paired_weighted_proof import verify_paired_weighted_semantic
from .paired_weighted_room import PairedWeightedRoom
from .root_frontier_proof import verify_root_foundation_semantic
from .root_frontier_room import RootFrontierRoom
from .approximation_frontier_proof import verify_approximation_foundation_semantic
from .approximation_frontier_room import ApproximationFrontierRoom
from .meta_autonomy_v3_benchmark import (
    BENCHMARK_VERSION,
    REQUIRED_SCORE,
    run_meta_autonomy_benchmark,
    sealed_cases,
    verify_meta_autonomy_report,
)
from .meta_autonomy_v3_room import MetaAutonomyV3Room
from .meta_autonomy_v4_benchmark import (
    deep_cases,
    run_deep_research_benchmark,
    transfer_case,
    verify_deep_research_report,
)
from .meta_autonomy_v4_room import MetaAutonomyV4Room
from .operator_frontier_v4 import (
    behavior_signature as operator_behavior_signature,
    explore_operator_worlds,
    operator_worlds,
    run_operator_frontier,
    verify_operator_frontier_report,
    verify_operator_program,
)
from .operator_frontier_v4_room import VerifiedOperatorRoom
from .operator_catalog_v5 import (
    additional_operator_specs,
    catalog_behavior_signature,
    discover_additional_operators,
    run_operator_catalog_v5,
    verify_additional_operator,
    verify_operator_catalog_v5_report,
)
from .operator_catalog_v5_room import VerifiedOperatorCatalogRoom
from .high_school_benchmark_v6 import (
    high_school_specs,
    run_high_school_benchmark,
    verify_high_school_program,
    verify_high_school_report,
)
from .high_school_room_v6 import HighSchoolCapabilityRoom
from .autonomous_operator_research_v7 import (
    posthoc_formula as autonomous_operator_formula,
    run_autonomous_operator_research_v7,
    verify_autonomous_operator_research_v7,
    verify_researched_operator,
)
from .autonomous_operator_room_v7 import AutonomousOperatorV7Room
from .foundation_expansion_v8 import (
    anonymous_foundation_worlds,
    replay_foundation_expansion_v8,
    run_foundation_expansion_v8,
    verify_foundation_expansion_v8,
)
from .foundation_expansion_v8_room import FoundationExpansionV8Room
from .linear_algebra_foundation_v9 import (
    anonymous_linear_worlds,
    replay_linear_algebra_foundation_v9,
    run_linear_algebra_foundation_v9,
    verify_linear_algebra_foundation_v9,
)
from .linear_algebra_foundation_v9_room import LinearAlgebraFoundationV9Room
from .strict_counter_foundation_v10 import (
    CounterFoundationProof,
    prove_counter_foundation,
    replay_counter_foundation,
)
from .strict_counter_foundation_v10_room import StrictCounterFoundationRoom
from .strict_partition_foundation_v11 import (
    PartitionFoundationProof,
    prove_partition_foundation,
    replay_partition_foundation,
)
from .strict_partition_foundation_v11_room import StrictPartitionFoundationRoom
from .strict_fold_foundation_v12 import (
    FoldFoundationProof,
    prove_fold_foundation,
    replay_fold_foundation,
)
from .strict_fold_foundation_v12_room import StrictFoldFoundationRoom
from .strict_foundation_expansion_v13 import (
    ExpansionProof,
    prove_integer_partition,
    prove_rational_integer_power,
    prove_signed_product,
)
from .strict_algebraic_closure_v14 import (
    ClosureProof,
    prove_congruence,
    prove_modular_fold,
    prove_modular_product,
    prove_rational_product,
)
from .self_extending_substrate_v15 import GenericLawMinerV15, MinedLaw, run_v15_acceptance
from .cold_start_semantics_v16 import (
    IndependentSemanticVerifierV16,
    OperatorVerificationV16,
    anonymous_primitive_workloads,
    run_v16_acceptance,
)
from .autonomous_research_loop_v17 import run_v17_acceptance
from .goal_driven_planner_v18 import (
    IndependentPlanVerifierV18,
    run_v18_acceptance,
    sealed_goal_problems,
)
from .autonomous_math_discovery_v19 import (
    expression_normal_form,
    replay_v19_report,
    run_v19_acceptance,
)
from .proof_driven_program_construction_v20 import (
    ProgramProofV20,
    prove_equation_solver,
    prove_pair_equivalence,
    prove_pair_operation,
    replay_v20_report,
    run_v20_acceptance,
)
from .directed_rational_construction_v21 import (
    prove_additive_group,
    prove_directed_equivalence,
    prove_ring_interaction,
    prove_translation_solver,
    replay_v21_report,
    run_v21_acceptance,
)
from .anonymous_physics_discovery_v22 import (
    generate_exchange_experiments,
    generate_kinematic_experiments,
    prove_conservation,
    prove_dimensions,
    prove_kinematic_programs,
    prove_normalization,
    replay_v22_report,
    run_v22_acceptance,
)
from .autonomous_physics_worlds_v23 import (
    prove_world_family,
    replay_v23_report,
    run_v23_acceptance,
    verify_world_independently,
)

__all__ = [
    "HiddenSequenceEnvironment",
    "HiddenIntegerGridEnvironment",
    "HiddenSymbolTraceEnvironment",
    "IndependentVerifier",
    "KnowledgeLedger",
    "KnowledgeState",
    "LedgerError",
    "FormulaRoomError",
    "FormulaSuccessRoom",
    "SuccessfulFormulaRecord",
    "MistakeLibrary",
    "MistakeLibraryError",
    "MistakeRecord",
    "MicroMistakeLibrary",
    "MicroMistakeLibraryError",
    "MicroMistakeRecord",
    "IndexedMistakeLibrary",
    "IndexedMistakeLibraryError",
    "IndexedMistakeRecord",
    "AdaptiveMistakeLibrary",
    "AdaptiveMistakeLibraryError",
    "AdaptiveMistakeRecord",
    "RelationMistakeLibrary",
    "RelationMistakeLibraryError",
    "RelationMistakeRecord",
    "SequenceWorldSpec",
    "VerificationCase",
    "VerificationReport",
    "program_family_signature",
    "relation_semantic_signature",
    "DOMAIN_NATURAL",
    "DOMAIN_NATURAL_PAIRS",
    "DOMAIN_NATURAL_POSITIVE_DIVISOR",
    "ProvenFormulaRecord",
    "UniversalFormulaCertificate",
    "UniversalFormulaRoom",
    "UniversalProofError",
    "UniversalProofVerification",
    "UniversalProofVerifier",
    "program_digest",
    "verify_state_window_semantic",
    "verify_micro_operator",
    "verify_micro_operator_batch",
    "SemanticRoomError",
    "VerifiedSemanticRoom",
    "verify_evolved_operator",
    "verify_evolved_operator_batch",
    "EvolvedSemanticRoomError",
    "VerifiedEvolvedSemanticRoom",
    "UniversalSemanticAudit",
    "UniversalSemanticAuditor",
    "UniversalSemanticAuditLoop",
    "verify_guarded_reduction_semantic",
    "verify_continuous_semantics",
    "verify_repeat_macro_semantic",
    "MASS_FORMULA_FIRST_OPCODE",
    "MASS_FORMULA_COUNT",
    "formula_id",
    "semantic_normal_form",
    "mass_formula_logic_signature",
    "verify_mass_formula_batch",
    "FormulaRejectionRoom",
    "verify_foundation_semantic",
    "FoundationSemanticRoom",
    "verify_reversible_foundation_semantic",
    "ReversibleFoundationRoom",
    "verify_directional_foundation_semantic",
    "DirectionalFoundationRoom",
    "verify_nested_foundation_semantic",
    "verify_partition_foundation_semantic",
    "NestedFoundationRoom",
    "PartitionFoundationRoom",
    "verify_recursive_foundation_semantic",
    "AutonomousFrontierRoom",
    "verify_distinct_foundation_semantic",
    "DistinctFrontierRoom",
    "verify_canonical_foundation_semantic",
    "CanonicalFrontierRoom",
    "verify_ratio_foundation_semantic",
    "RatioFrontierRoom",
    "verify_finite_mass_semantic",
    "FiniteMassRoom",
    "verify_joint_foundation_semantic",
    "JointFrontierRoom",
    "verify_weighted_foundation_semantic",
    "WeightedFrontierRoom",
    "verify_rational_algebra_semantic",
    "RationalAlgebraRoom",
    "verify_paired_weighted_semantic",
    "PairedWeightedRoom",
    "verify_root_foundation_semantic",
    "RootFrontierRoom",
    "verify_approximation_foundation_semantic",
    "ApproximationFrontierRoom",
    "BENCHMARK_VERSION",
    "REQUIRED_SCORE",
    "run_meta_autonomy_benchmark",
    "sealed_cases",
    "verify_meta_autonomy_report",
    "MetaAutonomyV3Room",
    "deep_cases",
    "run_deep_research_benchmark",
    "transfer_case",
    "verify_deep_research_report",
    "MetaAutonomyV4Room",
    "operator_behavior_signature",
    "explore_operator_worlds",
    "operator_worlds",
    "run_operator_frontier",
    "verify_operator_frontier_report",
    "verify_operator_program",
    "VerifiedOperatorRoom",
    "additional_operator_specs",
    "catalog_behavior_signature",
    "discover_additional_operators",
    "run_operator_catalog_v5",
    "verify_additional_operator",
    "verify_operator_catalog_v5_report",
    "VerifiedOperatorCatalogRoom",
    "high_school_specs",
    "run_high_school_benchmark",
    "verify_high_school_program",
    "verify_high_school_report",
    "HighSchoolCapabilityRoom",
    "autonomous_operator_formula",
    "run_autonomous_operator_research_v7",
    "verify_autonomous_operator_research_v7",
    "verify_researched_operator",
    "AutonomousOperatorV7Room",
    "anonymous_foundation_worlds",
    "replay_foundation_expansion_v8",
    "run_foundation_expansion_v8",
    "verify_foundation_expansion_v8",
    "FoundationExpansionV8Room",
    "anonymous_linear_worlds",
    "replay_linear_algebra_foundation_v9",
    "run_linear_algebra_foundation_v9",
    "verify_linear_algebra_foundation_v9",
    "LinearAlgebraFoundationV9Room",
    "CounterFoundationProof",
    "prove_counter_foundation",
    "replay_counter_foundation",
    "StrictCounterFoundationRoom",
    "PartitionFoundationProof",
    "prove_partition_foundation",
    "replay_partition_foundation",
    "StrictPartitionFoundationRoom",
    "FoldFoundationProof",
    "prove_fold_foundation",
    "replay_fold_foundation",
    "StrictFoldFoundationRoom",
    "ExpansionProof",
    "prove_integer_partition",
    "prove_rational_integer_power",
    "prove_signed_product",
    "ClosureProof",
    "prove_congruence",
    "prove_modular_fold",
    "prove_modular_product",
    "prove_rational_product",
    "GenericLawMinerV15",
    "MinedLaw",
    "run_v15_acceptance",
    "IndependentSemanticVerifierV16",
    "OperatorVerificationV16",
    "anonymous_primitive_workloads",
    "run_v16_acceptance",
    "run_v17_acceptance",
    "IndependentPlanVerifierV18",
    "run_v18_acceptance",
    "sealed_goal_problems",
    "expression_normal_form",
    "replay_v19_report",
    "run_v19_acceptance",
    "ProgramProofV20",
    "prove_equation_solver",
    "prove_pair_equivalence",
    "prove_pair_operation",
    "replay_v20_report",
    "run_v20_acceptance",
    "prove_additive_group",
    "prove_directed_equivalence",
    "prove_ring_interaction",
    "prove_translation_solver",
    "replay_v21_report",
    "run_v21_acceptance",
    "generate_exchange_experiments",
    "generate_kinematic_experiments",
    "prove_conservation",
    "prove_dimensions",
    "prove_kinematic_programs",
    "prove_normalization",
    "replay_v22_report",
    "run_v22_acceptance",
    "prove_world_family",
    "replay_v23_report",
    "run_v23_acceptance",
    "verify_world_independently",
]
