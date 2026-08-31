import os
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).resolve().parent

def load_policy(filename: str) -> str:
    """Loads markdown content of a policy file from the knowledge directory."""
    policy_path = KNOWLEDGE_DIR / filename
    if not policy_path.exists():
        raise FileNotFoundError(f"Policy file not found at: {policy_path}")
    
    with open(policy_path, "r", encoding="utf-8") as f:
        return f.read()

def get_policy_by_plan(plan_class: str) -> str:
    """Routes to the correct markdown policy based on the plan class string."""
    plan_lower = plan_class.lower()
    if "vision" in plan_lower or "csd n" in plan_lower:
        return load_policy("CSD_policy.md")
    elif "dental" in plan_lower:
        return load_policy("dental_ppo.md")
    elif "pharmacy" in plan_lower or "rx" in plan_lower:
        return load_policy("pharmacy_rx.md")
    else:
        # Fallback to the original policy if unknown
        return load_policy("CSD_policy.md")

def get_csd_policy() -> str:
    """Convenience getter for CSD-N policy (Legacy compatibility)."""
    return load_policy("CSD_policy.md")
