"""
NIS MVV Config — Canonical v1.1, immutable architecture
All values are derived from v1.1 spec. No redesign.
"""
import os
from dataclasses import dataclass

@dataclass
class DeliberationConfig:
    # Weights are [RECOMMENDED] defaults — tunable per deployment
    w_ambiguity: float = 0.25
    w_domain: float = 0.20
    w_tool: float = 0.15
    w_consequence: float = 0.25
    w_novelty: float = 0.15
    # Level thresholds [EXPLICIT]
    l0_max: float = 0.20
    l1_max: float = 0.40
    l2_max: float = 0.65
    l3_max: float = 0.85
    # L4 threshold lowered for A3/A4 [RECOMMENDED]
    ambiguity_threshold_default: float = 0.60
    ambiguity_threshold_l4: float = 0.35
    consequence_multiplier_min: float = 1.0
    consequence_multiplier_max: float = 1.5

@dataclass
class PriorityConfig:
    # Canonical literal order [EXPLICIT] Master Prompt Wins
    # 1 System, 2 Safety, 3 User explicit objective, 4 User preferences, 5 Task, 6 Personality
    # Variant flag [DERIVED] — opt-in only
    variant: str = "literal"  # "literal" | "task_first"
    # If variant=task_first, swaps 4↔5 but logs audit
    stack_literal = [
        "1_system_constraints",
        "2_safety_permission",
        "3_user_explicit_objective",
        "4_user_preferences",
        "5_task_requirements",
        "6_personality"
    ]
    stack_task_first = [
        "1_system_constraints",
        "2_safety_permission",
        "3_user_explicit_objective",
        "4_task_requirements",
        "5_user_preferences",
        "6_personality"
    ]

    def stack(self):
        if self.variant == "task_first":
            return self.stack_task_first
        return self.stack_literal

@dataclass
class MemoryConfig:
    # Freshness formula [RECOMMENDED]
    freshness_half_life_days: int = 180
    freshness_appendix_threshold: float = 0.5  # <0.5 → appendix unless L3+
    conversation_ttl_hours: int = 24
    behavioral_half_life_days: int = 90

@dataclass
class RuntimeConfig:
    deliberation: DeliberationConfig = None
    priority: PriorityConfig = None
    memory: MemoryConfig = None
    # N0.1 Proactive Tick [DERIVED] — gated and disabled by default [MVV requirement]
    proactive_tick_enabled: bool = False
    proactive_max_per_session: int = 1
    proactive_rate_limit_s: int = 300
    # Tool budgets per level [EXPLICIT]
    tool_budget: dict = None
    retrieval_budget: dict = None
    # Verification
    verification_max_loops: int = 3
    # Autonomy levels [DERIVED]
    autonomy_levels: list = None
    # Dense embeddings — v0.3-P1 E+A+B [DERIVED/RECOMMENDED]
    USE_DENSE: bool = False  # Feature flag, default FALSE until regression green (env NIS_USE_DENSE overrides)
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_cache_path: str = "data/memory/embeddings.json"
    embedding_version: str = "v0.3-P1"

    def __post_init__(self):
        if self.deliberation is None:
            self.deliberation = DeliberationConfig()
        if self.priority is None:
            self.priority = PriorityConfig()
        if self.memory is None:
            self.memory = MemoryConfig()
        if self.tool_budget is None:
            self.tool_budget = {0:0, 1:1, 2:3, 3:6, 4:10}
        if self.retrieval_budget is None:
            self.retrieval_budget = {0:0, 1:3, 2:6, 3:12, 4:12}
        if self.autonomy_levels is None:
            self.autonomy_levels = ["A0","A1","A2","A3","A4"]
        # Env override for app (PUBLIC vs SECRET separation kept)
        env_dense = os.getenv("NIS_USE_DENSE", "")
        if env_dense.lower() in ["true","1","yes"]:
            self.USE_DENSE = True
        elif env_dense.lower() in ["false","0","no"]:
            self.USE_DENSE = False
        # Allow model override via env (provider independence)
        env_model = os.getenv("NIS_EMBEDDING_MODEL", "")
        if env_model:
            self.embedding_model = env_model

CONFIG = RuntimeConfig()
