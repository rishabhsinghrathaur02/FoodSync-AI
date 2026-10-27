# FoodSync AI — Hackathon Prototype

**Tagline:** Synchronizing Surplus. Nourishing Lives.

A runnable Flask + SQLite prototype for coordinating eligible surplus food with NGO demand and NGO-provided delivery partners.

## What works
- Donor surplus registration
- NGO demand registration
- NGO delivery-partner registration
- SQLite persistence
- Eligibility gate: listings marked `Pending` or `Blocked` are never allocated
- Rule-based allocation with quantity, deadline, NGO demand and partner-capacity checks
- Delivery status tracking
- Simulated disruption and recovery attempt
- Impact metrics and agent activity log
- Demo data seeding

## Run in VS Code (Mac)
Open this folder in VS Code, then select **Terminal → New Terminal** and run:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open the local address printed in the terminal (normally http://127.0.0.1:5000).

## First demo
1. Click **Load demo data**.
2. Click **Run allocation**.
3. Review the deliveries and activity log.
4. Click **Simulate disruption** to make a delivery partner unavailable and attempt recovery.
5. Register a donor, NGO, or delivery partner to demonstrate live forms.

## Important scope and safety notes
- This is a hackathon simulation, not a production food-safety or dispatch system.
- Safety status is a hard eligibility gate, not an AI certification. A trained/authorised person must assess food under applicable requirements before real collection.
- The app uses estimated travel minutes, not live maps/GPS. Do not claim live routing.
- The demo data and metrics are simulated.
- For real deployment, add authentication/roles, secure hosting, audit controls, consent/privacy review, validated food-safety procedures, verified partner onboarding, and reliable notifications.

## Suggested 90-second demo
1. Load demo data and show donors, NGO demand, and partner availability.
2. Run allocation and explain why each match is feasible.
3. Simulate a disruption and show the recovery attempt / escalation if no alternative exists.
4. Finish on verified delivery metrics and the agent log.
