from random import randint


def generate_future_prediction(match_data, pressure_data):

    home_pressure = pressure_data["home"]["pressure"]
    away_pressure = pressure_data["away"]["pressure"]

    home_danger = pressure_data["home"]["danger"]
    away_danger = pressure_data["away"]["danger"]

    minute = match_data.get("minute", 0)

    total_home = home_pressure + home_danger
    total_away = away_pressure + away_danger

    prediction = "Match equilibrato"
    momentum_shift = "BALANCED"

    if total_home > total_away + 20:
        prediction = "Possibile goal Home nei prossimi 5 minuti"
        momentum_shift = "HOME"

    elif total_away > total_home + 20:
        prediction = "Possibile goal Away nei prossimi 5 minuti"
        momentum_shift = "AWAY"

    next_goal_probability = min(
        95,
        max(total_home, total_away)
    )

    counter_attack_risk = "LOW"

    if abs(total_home - total_away) > 30:
        counter_attack_risk = "HIGH"

    elif abs(total_home - total_away) > 15:
        counter_attack_risk = "MEDIUM"

    collapse_risk = "LOW"

    if minute > 70:
        collapse_risk = "MEDIUM"

    if minute > 82:
        collapse_risk = "HIGH"

    fatigue_warning = "NORMAL"

    if minute > 75:
        fatigue_warning = "ELEVATED"

    if minute > 85:
        fatigue_warning = "CRITICAL"

    confidence = randint(70, 98)

    return {
        "prediction_engine": {
            "next_goal_probability": next_goal_probability,
            "counter_attack_risk": counter_attack_risk,
            "collapse_risk": collapse_risk,
            "momentum_shift": momentum_shift,
            "fatigue_warning": fatigue_warning,
            "prediction": prediction,
            "confidence": confidence
        }
    }