# parser.py

def parse_attack_payload(raw_message, team_identifier):
    """
    Parses raw WebSocket messages into a standardized format.
    
    Returns:
        dict: Standardized alert data if an attack on our team is detected.
        None: If the attack is irrelevant to our team.
    """
    # 1. Adapt this block to match the specific platform's payload structure
    try:
        # Example assumes the platform sends clean JSON strings
        import json
        data = json.loads(raw_message)
    except Exception:
        # Fallback if raw data isn't strict JSON
        return None

    # 2. Extract crucial targets based on the platform's JSON scheme
    # (Change 'target_team', 'attacker', 'service' according to your current platform)
    target = data.get("target") or data.get("victim")
    attacker = data.get("attacker") or data.get("source", "Unknown Attacker")
    service = data.get("service") or data.get("flag_id", "Unknown Service")

    # 3. Check if our team is the one getting hit
    if target and str(team_identifier).lower() in str(target).lower():
        return {
            "attacked": True,
            "attacker": attacker,
            "service": service
        }

    return None