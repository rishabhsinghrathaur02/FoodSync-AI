def suitable_ngos(db, food_type):
    """Return NGOs with positive demand/capacity and compatible food preferences."""
    return db.execute("""
        SELECT * FROM ngos
        WHERE meal_demand > 0 AND capacity > 0
          AND (accepted_food = 'Both' OR accepted_food = ?)
        ORDER BY meal_demand DESC
    """, (food_type,)).fetchall()


def validate_demand(ngo):
    """Validate whether an NGO has enough demand and capacity."""
    if not ngo:
        return False

    return ngo["meal_demand"] > 0 and ngo["capacity"] > 0