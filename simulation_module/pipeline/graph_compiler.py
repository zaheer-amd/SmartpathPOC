import json
from pipeline.coordinate_transformer import transform_bbox

def compile_graph(
    raw_states: list[dict],
    frame_map: dict[str, str],
    output_path: str
) -> dict:
    """
    Compiles raw_metadata.json states + extracted frames into the
    final scenario_graph.json.
    
    Args:
        raw_states: List of state dicts from raw_metadata.json.
        frame_map:  Dict mapping state_id -> extracted PNG path.
        output_path: Where to write scenario_graph.json.
    
    Returns:
        The compiled graph dict.
    """
    compiled_states = []
    
    for i, state in enumerate(raw_states):
        state_id = state["state_id"]
        
        # Determine next state (linear chain; last state has null)
        next_state_id = raw_states[i + 1]["state_id"] if i < len(raw_states) - 1 else None
        
        # Transform bounding box
        css_coords = transform_bbox(state["bounding_box_1000"])
        
        compiled_state = {
            "state_id":       state_id,
            "sequence_index": i,
            "frame_image":    frame_map[state_id],  # relative path to PNG
            "action_type":    state["action_type"],  # "click" or "input"
            "ui_element_name": state["ui_element_name"],
            "instructional_hint": state["instructional_hint"],
            "css_coordinates": css_coords,  # {top, left, width, height} as %
            "next_state_id":  next_state_id,
        }
        
        # Only include expected_input_value for "input" actions
        if state["action_type"] == "input":
            compiled_state["expected_input_value"] = state["expected_input_value"]
        
        compiled_states.append(compiled_state)
    
    graph = {
        "version": "1.0.0",
        "generated_at": None,  # Set to ISO timestamp at build time
        "total_states": len(compiled_states),
        "initial_state_id": compiled_states[0]["state_id"],
        "states": compiled_states,
    }
    
    # Set timestamp
    from datetime import datetime, timezone
    graph["generated_at"] = datetime.now(timezone.utc).isoformat()
    
    # Write to disk
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2)
    
    print(f"  [OK] Compiled scenario_graph.json -> {output_path}")
    return graph
