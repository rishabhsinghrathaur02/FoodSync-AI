from datetime import datetime
from agents.demand_agent import suitable_ngos
from agents.verification_agent import log_event


def _minutes_until(deadline):
    try:
        due = datetime.fromisoformat(deadline)
        return max(0, int((due - datetime.now()).total_seconds() / 60))
    except (ValueError, TypeError):
        return 0


def run_allocation(db):
    """
    Deterministic, explainable allocation. Only safety-cleared listings can be assigned.
    Uses simplified location-independent travel estimates for a demo; not live routing.
    """
    listings = db.execute("""
        SELECT l.*, d.location AS donor_location, d.name AS donor_name
        FROM surplus_listings l JOIN donors d ON d.id = l.donor_id
        WHERE l.status = 'Eligible' AND l.safety_status = 'Eligible'
        ORDER BY l.deadline ASC, l.created_at ASC
    """).fetchall()

    created = 0
    notes = []
    for listing in listings:
        already = db.execute("""
            SELECT COALESCE(SUM(quantity), 0) AS total
            FROM deliveries
            WHERE listing_id = ? AND status != 'Cancelled'
        """, (listing["id"],)).fetchone()["total"]
        remaining = listing["quantity"] - already
        if remaining <= 0:
            continue

        ngos = suitable_ngos(db, listing["food_type"])
        # Urgent listings first; NGO demand is the primary matching score in this prototype.
        candidates = sorted(
            ngos,
            key=lambda n: (
                -min(n["meal_demand"], n["capacity"]),
                n["location"] != listing["donor_location"],
                n["id"]
            )
        )

        for ngo in candidates:
            if remaining <= 0:
                break
            demand_used = db.execute("""
                SELECT COALESCE(SUM(quantity), 0) AS total FROM deliveries
                WHERE ngo_id = ? AND status != 'Cancelled'
            """, (ngo["id"],)).fetchone()["total"]
            need = max(0, min(ngo["meal_demand"], ngo["capacity"]) - demand_used)
            if need <= 0:
                continue

            partners = db.execute("""
                SELECT * FROM delivery_partners
                WHERE ngo_id = ? AND available = 1 AND capacity > 0
                ORDER BY capacity ASC, id ASC
            """, (ngo["id"],)).fetchall()
            if not partners:
                continue

            # Assign the partner with the smallest sufficient capacity where possible.
            partner = next((p for p in partners if p["capacity"] >= min(remaining, need)), partners[-1])
            qty = min(remaining, need, partner["capacity"])
            eta = 15 if listing["donor_location"] == ngo["location"] else 35
            if _minutes_until(listing["deadline"]) < eta:
                notes.append(f"{listing['donor_name']}: skipped {ngo['name']} because estimated travel time exceeds the deadline.")
                continue

            now = datetime.now().isoformat(timespec="minutes")
            db.execute("""
                INSERT INTO deliveries
                (listing_id, ngo_id, partner_id, quantity, estimated_minutes, status, created_at, updated_at)
                VALUES(?,?,?,?,?,'Assigned',?,?)
            """, (listing["id"], ngo["id"], partner["id"], qty, eta, now, now))
            # Reserve this partner until the delivery status is updated; one assignment at a time.
            db.execute("UPDATE delivery_partners SET available = 0 WHERE id = ?", (partner["id"],))
            remaining -= qty
            created += 1
            log_event(db, "Allocation Intelligence",
                      f"Assigned {qty} portions from {listing['donor_name']} to {ngo['name']} via {partner['name']} (estimated {eta} min).")

        if remaining > 0:
            notes.append(f"{listing['donor_name']}: {remaining} portions remain unallocated; no currently feasible match.")
    if created:
        message = f"Created {created} delivery assignment(s). Review partner availability and delivery statuses."
    else:
        message = "No new feasible assignments. Check safety eligibility, NGO demand, partner availability and deadlines."
    if notes:
        log_event(db, "Allocation Intelligence", " | ".join(notes[:5]))
    return {"created": created, "message": message, "notes": notes}
