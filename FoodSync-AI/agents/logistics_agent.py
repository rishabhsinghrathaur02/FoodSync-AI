from datetime import datetime
from agents.verification_agent import log_event


def simulate_disruption(db):
    """
    Demo scenario: make the first assigned partner unavailable and attempt to
    reassign its delivery to another available partner with enough capacity.
    """
    delivery = db.execute("""
        SELECT x.*, p.name AS partner_name, p.ngo_id AS partner_ngo_id
        FROM deliveries x
        LEFT JOIN delivery_partners p ON p.id = x.partner_id
        WHERE x.status = 'Assigned'
        ORDER BY x.id ASC LIMIT 1
    """).fetchone()

    if not delivery:
        return {"recovered": False, "message": "No delivery with status Assigned to disrupt. Run allocation first."}

    old_partner_id = delivery["partner_id"]
    old_partner_name = delivery["partner_name"] or "Unknown partner"
    db.execute("UPDATE delivery_partners SET available = 0 WHERE id = ?", (old_partner_id,))
    db.execute("""
        UPDATE deliveries SET disruption_note = ?, updated_at = ? WHERE id = ?
    """, ("Simulated partner disruption", datetime.now().isoformat(timespec="minutes"), delivery["id"]))

    replacement = db.execute("""
        SELECT * FROM delivery_partners
        WHERE available = 1 AND capacity >= ?
        ORDER BY capacity ASC, id ASC LIMIT 1
    """, (delivery["quantity"],)).fetchone()

    if replacement:
        db.execute("UPDATE deliveries SET partner_id = ?, disruption_note = ?, updated_at = ? WHERE id = ?",
                   (replacement["id"], f"Recovered from {old_partner_name}; reassigned to {replacement['name']}.",
                    datetime.now().isoformat(timespec="minutes"), delivery["id"]))
        db.execute("UPDATE delivery_partners SET available = 0 WHERE id = ?", (replacement["id"],))
        log_event(db, "Logistics & Recovery",
                  f"Disruption detected for delivery #{delivery['id']}. Reassigned from {old_partner_name} to {replacement['name']}.")
        return {"recovered": True,
                "message": f"Delivery #{delivery['id']} recovered: {old_partner_name} → {replacement['name']}."}

    log_event(db, "Logistics & Recovery",
              f"Disruption detected for delivery #{delivery['id']}; no feasible replacement partner. Coordinator alert required.")
    return {"recovered": False,
            "message": f"Delivery #{delivery['id']} disrupted. No feasible replacement partner; coordinator alert required."}
