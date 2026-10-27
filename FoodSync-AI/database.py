import os
import sqlite3
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "foodsynchronization.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS donors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        location TEXT NOT NULL,
        contact TEXT DEFAULT '',
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS ngos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        location TEXT NOT NULL,
        meal_demand INTEGER NOT NULL DEFAULT 0,
        capacity INTEGER NOT NULL DEFAULT 0,
        accepted_food TEXT NOT NULL DEFAULT 'Both',
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS surplus_listings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        donor_id INTEGER NOT NULL REFERENCES donors(id),
        food_type TEXT NOT NULL,
        quantity INTEGER NOT NULL CHECK(quantity > 0),
        ready_time TEXT NOT NULL,
        deadline TEXT NOT NULL,
        safety_status TEXT NOT NULL DEFAULT 'Pending',
        status TEXT NOT NULL DEFAULT 'Pending',
        notes TEXT DEFAULT '',
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS delivery_partners (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ngo_id INTEGER NOT NULL REFERENCES ngos(id),
        name TEXT NOT NULL,
        transport TEXT NOT NULL,
        capacity INTEGER NOT NULL CHECK(capacity > 0),
        available INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS deliveries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        listing_id INTEGER NOT NULL REFERENCES surplus_listings(id),
        ngo_id INTEGER NOT NULL REFERENCES ngos(id),
        partner_id INTEGER REFERENCES delivery_partners(id),
        quantity INTEGER NOT NULL CHECK(quantity > 0),
        estimated_minutes INTEGER NOT NULL DEFAULT 30,
        status TEXT NOT NULL DEFAULT 'Assigned',
        disruption_note TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS agent_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent TEXT NOT NULL,
        message TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)
    db.commit()
    db.close()


def seed_demo_data(db):
    count = db.execute("SELECT COUNT(*) AS n FROM donors").fetchone()["n"]
    if count > 0:
        return "Database already contains records; demo data was not duplicated."

    now = datetime.now()
    stamp = now.isoformat(timespec="minutes")
    deadline = (now + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M")
    ready = now.strftime("%Y-%m-%dT%H:%M")

    donor_ids = []
    for name, loc in [
        ("Green Bowl Cafe", "Sector 14"),
        ("Sunrise Banquet", "Model Town"),
        ("Campus Kitchen", "University Road"),
    ]:
        cur = db.execute("INSERT INTO donors(name, location, contact, created_at) VALUES(?,?,?,?)",
                         (name, loc, "demo@example.org", stamp))
        donor_ids.append(cur.lastrowid)

    ngo_ids = []
    for name, loc, demand, capacity, food in [
        ("Hope Shelter", "Sector 15", 60, 100, "Both"),
        ("Community Meal Centre", "Model Town", 45, 80, "Vegetarian"),
        ("Helping Hands NGO", "University Road", 35, 60, "Both"),
    ]:
        cur = db.execute("""
            INSERT INTO ngos(name, location, meal_demand, capacity, accepted_food, created_at)
            VALUES(?,?,?,?,?,?)
        """, (name, loc, demand, capacity, food, stamp))
        ngo_ids.append(cur.lastrowid)

    listings = [
        (donor_ids[0], "Vegetarian", 50, "Eligible", "Freshly prepared demo listing"),
        (donor_ids[1], "Both", 70, "Eligible", "Banquet surplus demo listing"),
        (donor_ids[2], "Vegetarian", 30, "Pending", "Pending safety review; must not be allocated"),
    ]
    for donor_id, food, qty, safety, notes in listings:
        status = "Eligible" if safety == "Eligible" else "Pending"
        db.execute("""
            INSERT INTO surplus_listings
            (donor_id, food_type, quantity, ready_time, deadline, safety_status, status, notes, created_at)
            VALUES(?,?,?,?,?,?,?,?,?)
        """, (donor_id, food, qty, ready, deadline, safety, status, notes, stamp))

    for ngo_id, name, transport, cap, available in [
        (ngo_ids[0], "Hope Bike Partner 1", "Motorcycle", 40, 1),
        (ngo_ids[1], "Meal Centre Van 1", "Van", 80, 1),
        (ngo_ids[2], "Helping Hands Partner 1", "Motorcycle", 35, 1),
        (ngo_ids[0], "Hope Backup Partner", "Van", 60, 1),
    ]:
        db.execute("""
            INSERT INTO delivery_partners(ngo_id, name, transport, capacity, available, created_at)
            VALUES(?,?,?,?,?,?)
        """, (ngo_id, name, transport, cap, available, stamp))

    db.execute("INSERT INTO agent_logs(agent, message, created_at) VALUES(?,?,?)",
               ("System", "Demo data loaded. All demo records are simulated.", stamp))
    return "Demo data loaded. All records are simulated; run allocation to create delivery plans."
