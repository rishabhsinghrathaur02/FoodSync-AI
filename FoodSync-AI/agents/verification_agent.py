from datetime import datetime


def log_event(db, agent, message):
    db.execute("INSERT INTO agent_logs(agent, message, created_at) VALUES(?,?,?)",
               (agent, message, datetime.now().isoformat(timespec="minutes")))


def dashboard_metrics(db):
    donors = db.execute("SELECT COUNT(*) AS n FROM donors").fetchone()["n"]
    ngos = db.execute("SELECT COUNT(*) AS n FROM ngos").fetchone()["n"]
    eligible = db.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS n FROM surplus_listings
        WHERE status = 'Eligible' AND safety_status = 'Eligible'
    """).fetchone()["n"]
    assigned = db.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS n FROM deliveries
        WHERE status IN ('Assigned', 'Picked Up', 'In Transit', 'Received by NGO', 'Distribution Confirmed')
    """).fetchone()["n"]
    received = db.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS n FROM deliveries
        WHERE status IN ('Received by NGO', 'Distribution Confirmed')
    """).fetchone()["n"]
    distributed = db.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS n FROM deliveries
        WHERE status = 'Distribution Confirmed'
    """).fetchone()["n"]
    pending_safety = db.execute("""
        SELECT COUNT(*) AS n FROM surplus_listings
        WHERE safety_status != 'Eligible' OR status != 'Eligible'
    """).fetchone()["n"]
    unmet = db.execute("""
        SELECT COALESCE(SUM(MAX(0, n.meal_demand - COALESCE(a.allocated, 0))), 0) AS n
        FROM ngos n
        LEFT JOIN (
            SELECT ngo_id, SUM(quantity) AS allocated
            FROM deliveries WHERE status != 'Cancelled'
            GROUP BY ngo_id
        ) a ON a.ngo_id = n.id
    """).fetchone()["n"]
    total_deliveries = db.execute("SELECT COUNT(*) AS n FROM deliveries").fetchone()["n"]
    on_time = db.execute("""
        SELECT COUNT(*) AS n FROM deliveries x
        JOIN surplus_listings l ON l.id = x.listing_id
        WHERE x.status IN ('Received by NGO', 'Distribution Confirmed')
          AND datetime(x.updated_at) <= datetime(l.deadline)
    """).fetchone()["n"]
    on_time_rate = round(on_time / max(1, received_delivery_count(db)) * 100)
    return {
        "donors": donors,
        "ngos": ngos,
        "eligible_portions": eligible,
        "assigned_portions": assigned,
        "received_portions": received,
        "distributed_portions": distributed,
        "pending_safety": pending_safety,
        "unmet_demand": unmet,
        "deliveries": total_deliveries,
        "on_time_rate": on_time_rate
    }


def received_delivery_count(db):
    return db.execute("""
        SELECT COUNT(*) AS n FROM deliveries
        WHERE status IN ('Received by NGO', 'Distribution Confirmed')
    """).fetchone()["n"]
