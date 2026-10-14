import os
from pathlib import Path
import re

KNOWLEDGE_DIR = Path(__file__).resolve().parent

# Global in-memory index
# Structure: { "vision csd-n": { "Policy Overview": "...", "Coverage Limits": "..." } }
POLICY_INDEX: dict[str, dict[str, str]] = {}

def get_plan_class_key(text: str) -> str:
    """Normalizes a plan class string for index lookup."""
    t = text.lower()
    if "vision" in t or "csd n" in t:
        return "vision csd-n"
    elif "dental" in t:
        return "dental ppo"
    elif "pharmacy" in t or "rx" in t:
        return "pharmacy rx"
    return "vision csd-n" # fallback

def build_index() -> None:
    """Reads all .md files in knowledge/ (or knowledge/policies/) dir and builds the section index."""
    global POLICY_INDEX
    POLICY_INDEX.clear()
    
    policies_dir = KNOWLEDGE_DIR / "policies"
    md_files = list(policies_dir.glob("*.md")) if policies_dir.exists() else []
    if not md_files:
        md_files = list(KNOWLEDGE_DIR.glob("*.md"))
    
    for md_file in md_files:
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Extract the main plan class from the first H1
        h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if not h1_match:
            continue
            
        plan_key = get_plan_class_key(h1_match.group(1))
        if plan_key not in POLICY_INDEX:
            POLICY_INDEX[plan_key] = {}
            
        # Split into sections by H2 (##)
        sections = re.split(r"^##\s+", content, flags=re.MULTILINE)
        
        # The first chunk is everything before the first H2 (usually the title/overview)
        POLICY_INDEX[plan_key]["Overview"] = sections[0].strip()
        
        for section in sections[1:]:
            lines = section.split("\n", 1)
            title = lines[0].strip()
            body = lines[1].strip() if len(lines) > 1 else ""
            POLICY_INDEX[plan_key][title] = f"## {title}\n{body}"

def search_policy(plan_class: str, query: str, top_k: int = 2) -> list[dict]:
    """
    Mock semantic search. For this mock, we just do a naive keyword 
    intersection against the section titles and bodies.
    """
    plan_key = get_plan_class_key(plan_class)
    sections = POLICY_INDEX.get(plan_key, {})
    
    if not sections:
        return []
        
    query_words = set(query.lower().split())
    
    scored_sections = []
    for title, content in sections.items():
        text_to_search = (title + " " + content).lower()
        score = sum(1 for word in query_words if word in text_to_search)
        
        # Add a baseline score to always return *something* if no keywords match perfectly
        # just to mock how RAG always returns nearest neighbors
        score += 0.1 
        
        scored_sections.append({
            "score": score,
            "section_title": title,
            "content": content
        })
        
    # Sort by score descending
    scored_sections.sort(key=lambda x: x["score"], reverse=True)
    
    # Return top K, formatting as the mock Azure service would
    results = []
    for i, sec in enumerate(scored_sections[:top_k]):
        results.append({
            "source": "mock-azure-ai-search",
            "index": "smartpath-policies",
            "score": round(sec["score"], 2),
            "section_title": sec["section_title"],
            "content": sec["content"]
        })
        
    return results

def get_full_policy(plan_class: str) -> str:
    """Fallback: reconstructs the full policy doc from the index."""
    plan_key = get_plan_class_key(plan_class)
    sections = POLICY_INDEX.get(plan_key, {})
    
    if not sections:
        return f"No policy found for {plan_class}."
        
    parts = []
    if "Overview" in sections:
        parts.append(sections["Overview"])
        
    for title, content in sections.items():
        if title != "Overview":
            parts.append(content)
            
    return "\n\n".join(parts)
