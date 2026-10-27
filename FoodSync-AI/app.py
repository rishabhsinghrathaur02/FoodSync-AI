from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from database import init_db, get_db, seed_demo_data
from agents.surplus_agent import validate_surplus
from agents.demand_agent import validate_demand
from agents.allocation_agent import run_allocation
from agents.logistics_agent import simulate_disruption
from agents.verification_agent import dashboard_metrics, log_event

app = Flask(__name__)
app.secret_key = "foodsynchronization-demo-secret-change-before-deployment"
init_db()


@app.template_filter("pretty_time")
def pretty_time(value):
    if not value:
        return "—"
    try:
        return datetime.fromisoformat(value).strftime("%d %b, %H:%M")
    except (ValueError, TypeError):
        return value


@app.route("/")
def index():
    db = get_db()
    metrics = dashboard_metrics(db)
    donors = db.execute("SELECT * FROM donors ORDER BY id DESC").fetchall()
    listings = db.execute("""
        SELECT l.*, d.name AS donor_name, d.location AS donor_location
        FROM surplus_listings l JOIN donors d ON d.id = l.donor_id
        ORDER BY l.id DESC
    """).fetchall()
    ngos = db.execute("SELECT * FROM ngos ORDER BY id DESC").fetchall()
    partners = db.execute("""
        SELECT p.*, n.name AS ngo_name
        FROM delivery_partners p JOIN ngos n ON n.id = p.ngo_id
        ORDER BY p.id DESC
    """).fetchall()
    deliveries = db.execute("""
        SELECT x.*, l.food_type, l.quantity AS listed_quantity,
               d.name AS donor_name, n.name AS ngo_name,
               p.name AS partner_name
        FROM deliveries x
        JOIN surplus_listings l ON l.id = x.listing_id
        JOIN donors d ON d.id = l.donor_id
        JOIN ngos n ON n.id = x.ngo_id
        LEFT JOIN delivery_partners p ON p.id = x.partner_id
        ORDER BY x.id DESC
    """).fetchall()
    events = db.execute("SELECT * FROM agent_logs ORDER BY id DESC LIMIT 12").fetchall()
    db.close()
    return render_template(
        "index.html", metrics=metrics, donors=donors, listings=listings,
        ngos=ngos, partners=partners, deliveries=deliveries, events=events
    )


@app.post("/donors")
def add_donor():
    name = request.form.get("name", "").strip()
    location = request.form.get("location", "").strip()
    contact = request.form.get("contact", "").strip()
    if not name or not location:
        flash("Donor name and pickup location are required.", "error")
        return redirect(url_for("index"))
    db = get_db()
    db.execute("INSERT INTO donors(name, location, contact, created_at) VALUES(?,?,?,?)",
               (name, location, contact, datetime.now().isoformat(timespec="minutes")))
    db.commit()
    log_event(db, "Surplus Intelligence", f"Registered food donor: {name}")
    db.close()
    flash("Donor registered.", "success")
    return redirect(url_for("index"))


@app.post("/surplus")
def add_surplus():
    try:
        donor_id = int(request.form.get("donor_id", "0"))
        quantity = int(request.form.get("quantity", "0"))
        ready_time = request.form.get("ready_time", "").strip()
        deadline = request.form.get("deadline", "").strip()
        food_type = request.form.get("food_type", "Vegetarian")
        safety_status = request.form.get("safety_status", "Pending")
        notes = request.form.get("notes", "").strip()
        if quantity <= 0 or not ready_time or not deadline:
            raise ValueError
    except ValueError:
        flash("Enter a valid donor, positive quantity, ready time and deadline.", "error")
        return redirect(url_for("index"))
    db = get_db()
    donor = db.execute("SELECT id FROM donors WHERE id=?", (donor_id,)).fetchone()
    if not donor:
        db.close()
        flash("Select an existing donor first.", "error")
        return redirect(url_for("index"))
    result = validate_surplus(quantity, ready_time, deadline, safety_status)
    status = result["status"]
    db.execute("""
        INSERT INTO surplus_listings
        (donor_id, food_type, quantity, ready_time, deadline, safety_status, status, notes, created_at)
        VALUES(?,?,?,?,?,?,?,?,?)
    """, (donor_id, food_type, quantity, ready_time, deadline, safety_status, status,
          notes, datetime.now().isoformat(timespec="minutes")))
    db.commit()
    log_event(db, "Surplus Intelligence", result["message"])
    db.close()
    flash(result["message"], "success" if status == "Eligible" else "warning")
    return redirect(url_for("index"))


@app.post("/ngos")
def add_ngo():
    name = request.form.get("name", "").strip()
    location = request.form.get("location", "").strip()
    demand = request.form.get("demand", "0")
    capacity = request.form.get("capacity", "0")
    accepted = request.form.get("accepted_food", "Both")
    if not name or not location:
        flash("NGO name and location are required.", "error")
        return redirect(url_for("index"))
    try:
        demand, capacity = int(demand), int(capacity)
        if demand < 0 or capacity < 0:
            raise ValueError
    except ValueError:
        flash("Demand and capacity must be non-negative numbers.", "error")
        return redirect(url_for("index"))
    db = get_db()
    db.execute("""
        INSERT INTO ngos(name, location, meal_demand, capacity, accepted_food, created_at)
        VALUES(?,?,?,?,?,?)
    """, (name, location, demand, capacity, accepted, datetime.now().isoformat(timespec="minutes")))
    db.commit()
    log_event(db, "Demand Intelligence", f"Registered NGO {name}: demand {demand} portions.")
    db.close()
    flash("NGO and current demand registered.", "success")
    return redirect(url_for("index"))


@app.post("/partners")
def add_partner():
    name = request.form.get("name", "").strip()
    ngo_id = request.form.get("ngo_id", "0")
    transport = request.form.get("transport", "Motorcycle")
    capacity = request.form.get("capacity", "0")
    available = 1 if request.form.get("available") == "on" else 0
    if not name:
        flash("Partner name is required.", "error")
        return redirect(url_for("index"))
    try:
        ngo_id, capacity = int(ngo_id), int(capacity)
        if capacity <= 0:
            raise ValueError
    except ValueError:
        flash("Choose an NGO and enter a positive carrying capacity.", "error")
        return redirect(url_for("index"))
    db = get_db()
    ngo = db.execute("SELECT id FROM ngos WHERE id=?", (ngo_id,)).fetchone()
    if not ngo:
        db.close()
        flash("Register an NGO before adding its delivery partner.", "error")
        return redirect(url_for("index"))
    db.execute("""
        INSERT INTO delivery_partners(ngo_id, name, transport, capacity, available, created_at)
        VALUES(?,?,?,?,?,?)
    """, (ngo_id, name, transport, capacity, available, datetime.now().isoformat(timespec="minutes")))
    db.commit()
    log_event(db, "Logistics & Recovery", f"Registered NGO delivery partner {name}.")
    db.close()
    flash("NGO delivery partner registered.", "success")
    return redirect(url_for("index"))


@app.post("/allocate")
def allocate():
    db = get_db()
    result = run_allocation(db)
    db.commit()
    db.close()
    flash(result["message"], "success" if result["created"] else "warning")
    return redirect(url_for("index"))


@app.post("/disruption")
def disruption():
    db = get_db()
    result = simulate_disruption(db)
    db.commit()
    db.close()
    flash(result["message"], "success" if result["recovered"] else "warning")
    return redirect(url_for("index"))


@app.post("/seed")
def seed():
    db = get_db()
    result = seed_demo_data(db)
    db.commit()
    db.close()
    flash(result, "success")
    return redirect(url_for("index"))


@app.post("/delivery/<int:delivery_id>/status")
def update_delivery(delivery_id):
    new_status = request.form.get("status", "")
    allowed = {"Picked Up", "In Transit", "Received by NGO", "Distribution Confirmed", "Cancelled"}
    if new_status not in allowed:
        flash("Invalid delivery status.", "error")
        return redirect(url_for("index"))
    db = get_db()
    row = db.execute("SELECT id FROM deliveries WHERE id=?", (delivery_id,)).fetchone()
    if not row:
        db.close()
        flash("Delivery not found.", "error")
        return redirect(url_for("index"))
    delivery = db.execute("SELECT partner_id FROM deliveries WHERE id=?", (delivery_id,)).fetchone()
    db.execute("UPDATE deliveries SET status=?, updated_at=? WHERE id=?",
               (new_status, datetime.now().isoformat(timespec="minutes"), delivery_id))
    if new_status in {"Received by NGO", "Distribution Confirmed", "Cancelled"} and delivery and delivery["partner_id"]:
        db.execute("UPDATE delivery_partners SET available=1 WHERE id=?", (delivery["partner_id"],))
    log_event(db, "Verification & Impact", f"Delivery #{delivery_id} status changed to {new_status}.")
    db.commit()
    db.close()
    flash("Delivery status updated.", "success")
    return redirect(url_for("index"))


@app.get("/api/metrics")
def api_metrics():
    db = get_db()
    metrics = dashboard_metrics(db)
    db.close()
    return jsonify(metrics)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
