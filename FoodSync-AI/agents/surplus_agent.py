from datetime import datetime


def validate_surplus(quantity, ready_time, deadline, safety_status):
    """Validate submitted fields; this does not certify food safety."""
    if quantity <= 0:
        return {"status": "Blocked", "message": "Surplus blocked: quantity must be positive."}
    try:
        ready = datetime.fromisoformat(ready_time)
        due = datetime.fromisoformat(deadline)
        if due <= ready:
            return {"status": "Blocked", "message": "Surplus blocked: deadline must be after ready time."}
    except ValueError:
        return {"status": "Blocked", "message": "Surplus blocked: use valid date/time values."}

    if safety_status != "Eligible":
        return {
            "status": "Pending" if safety_status == "Pending" else "Blocked",
            "message": f"Surplus listing recorded as {safety_status}; it cannot be allocated until cleared."
        }

    return {
        "status": "Eligible",
        "message": f"Surplus record validated ({quantity} portions). Human/authorised safety checks remain required."
    }
