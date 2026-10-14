import json

def patch():
    with open('simulation_module/inputs/raw_metadata.json', 'r') as f:
        data = json.load(f)
    
    # State mapping updates
    # Format: state_id -> new bounding_box_1000
    updates = {
        "STATE_01": [430, 620, 480, 930], # Chat input (below mentor header)
        "STATE_02": [430, 930, 480, 975], # Send button
        "STATE_03": [580, 20, 620, 350],  # 4th expander
        "STATE_04": [510, 20, 550, 350],  # 3rd expander
        "STATE_05": [700, 40, 750, 490],  # Eligible amount
        "STATE_06": [700, 510, 750, 960], # Out of pocket
        "STATE_07": [800, 40, 850, 490],  # Decision dropdown
        "STATE_08": [850, 40, 890, 490],  # Approve option
        "STATE_09": [800, 510, 850, 960], # EOB Dropdown
        "STATE_10": [850, 510, 890, 960], # EOB option
        "STATE_11": [920, 40, 970, 195],  # Submit button
    }
    
    for state in data:
        sid = state['state_id']
        if sid in updates:
            state['bounding_box_1000'] = updates[sid]
            
    with open('simulation_module/inputs/raw_metadata.json', 'w') as f:
        json.dump(data, f, indent=4)

if __name__ == "__main__":
    patch()
