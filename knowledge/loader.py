import os
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).resolve().parent

def load_policy(filename: str = "CSD_policy.md") -> str:
    """Loads markdown content of a policy file from the knowledge directory."""
    policy_path = KNOWLEDGE_DIR / filename
    if not policy_path.exists():
        raise FileNotFoundError(f"Policy file not found at: {policy_path}")
    
    with open(policy_path, "r", encoding="utf-8") as f:
        return f.read()

def get_csd_policy() -> str:
    """Convenience getter for CSD-N policy."""
    return load_policy("CSD_policy.md")
