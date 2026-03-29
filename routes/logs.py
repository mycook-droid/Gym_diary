from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, WorkoutLog, Exercise, WorkoutSplit, SplitDay
from datetime import date, datetime, timedelta
from collections import defaultdict

logs_bp = Blueprint("logs", __name__)

TRACKED_MUSCLES = ["chest", "back", "legs", "shoulders", "biceps", "triceps"]

EXERCISE_MUSCLE_MAP = {
    "bench press": {"chest": 0.6, "shoulders": 0.25, "triceps": 0.15},
    "incline dumbbell press": {"chest": 0.55, "shoulders": 0.3, "triceps": 0.15},
    "incline bench press": {"chest": 0.55, "shoulders": 0.3, "triceps": 0.15},
    "cable fly": {"chest": 0.85, "shoulders": 0.1, "triceps": 0.05},
    "overhead press": {"shoulders": 0.55, "triceps": 0.3, "chest": 0.15},
    "lateral raises": {"shoulders": 1.0},
    "face pulls": {"shoulders": 0.8, "back": 0.2},
    "tricep pushdown": {"triceps": 1.0},
    "overhead tricep extension": {"triceps": 1.0},
    "skull crushers": {"triceps": 1.0},
    "deadlift": {"back": 0.4, "legs": 0.4, "shoulders": 0.1, "biceps": 0.1},
    "barbell row": {"back": 0.75, "biceps": 0.25},
    "seated cable row": {"back": 0.75, "biceps": 0.25},
    "lat pulldown": {"back": 0.75, "biceps": 0.25},
    "pull ups": {"back": 0.7, "biceps": 0.3},
    "barbell curl": {"biceps": 1.0},
    "hammer curl": {"biceps": 1.0},
    "incline dumbbell curl": {"biceps": 1.0},
    "bicep curl": {"biceps": 1.0},
    "squat": {"legs": 0.9, "back": 0.1},
    "romanian deadlift": {"legs": 0.75, "back": 0.25},
    "leg press": {"legs": 1.0},
    "leg curl": {"legs": 1.0},
    "bulgarian split squat": {"legs": 1.0},
}

MUSCLE_GROUP_FALLBACK = {
    "chest": {"chest": 1.0},
    "back": {"back": 1.0},
    "rear delts": {"shoulders": 1.0},
    "shoulders": {"shoulders": 1.0},
    "triceps": {"triceps": 1.0},
    "biceps": {"biceps": 1.0},
    "quads": {"legs": 1.0},
    "hamstrings": {"legs": 1.0},
    "calves": {"legs": 1.0},
    "legs": {"legs": 1.0},
}


def intensity_factor_for_reps(reps):
    reps = int(reps or 0)
    if reps <= 5:
        return 1.0
    if reps <= 10:
        return 0.85
    if reps <= 15:
        return 0.7
    return 0.5


def get_distribution_for_exercise(exercise_name, muscle_group):
    key = (exercise_name or "").strip().lower()
    if key in EXERCISE_MUSCLE_MAP:
        return EXERCISE_MUSCLE_MAP[key]

    for known_name, distribution in EXERCISE_MUSCLE_MAP.items():
        if known_name in key:
            return distribution

    group_key = (muscle_group or "").strip().lower()
    return MUSCLE_GROUP_FALLBACK.get(group_key, {})


# ─── LOG A WORKOUT SET ────────────────────────────────────────────────────────

@logs_bp.route("/", methods=["POST"])
@jwt_required()
def log_set():
    """
    Log one or multiple sets for an exercise.
    Body: { exercise_id, date, sets: [{set_number, reps, weight, notes}] }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json()

    required = ["exercise_id", "sets"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400

    # Verify exercise belongs to this user
    exercise = Exercise.query.get(data["exercise_id"])
    if not exercise or exercise.split_day.split.user_id != user_id:
        return jsonify({"error": "Exercise not found"}), 404

    # Use today if no date provided
    log_date = date.today()
    if data.get("date"):
        try:
            log_date = date.fromisoformat(data["date"])
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    if not isinstance(data["sets"], list) or len(data["sets"]) == 0:
        return jsonify({"error": "sets must be a non-empty list"}), 400

    created_logs = []
    for s in data["sets"]:
        if s.get("reps") is None or s.get("weight") is None:
            return jsonify({"error": "Each set needs reps and weight"}), 400

        log = WorkoutLog(
            user_id=user_id,
            exercise_id=data["exercise_id"],
            date=log_date,
            set_number=s.get("set_number", 1),
            reps=s["reps"],
            weight=s["weight"],
            notes=s.get("notes")
        )
        db.session.add(log)
        created_logs.append(log)

    db.session.commit()

    return jsonify({
        "message": f"{len(created_logs)} set(s) logged",
        "logs": [l.to_dict() for l in created_logs]
    }), 201


# ─── GET TODAY'S WORKOUT ──────────────────────────────────────────────────────

@logs_bp.route("/today", methods=["GET"])
@jwt_required()
def get_today():
    """
    Returns the current training day based on split progression (not calendar weekday).
    If user already logged today, keep showing the same day to continue that session.
    """
    user_id = int(get_jwt_identity())

    active_split = WorkoutSplit.query.filter_by(user_id=user_id, is_active=True).first()
    if not active_split:
        return jsonify({"error": "No active split. Please activate a split first."}), 404

    split_days = SplitDay.query.filter_by(split_id=active_split.id).order_by(SplitDay.id).all()
    training_days = [d for d in split_days if d.day_label != "Rest" and len(d.exercises) > 0]

    if not training_days:
        return jsonify({"message": "Rest day. No workout today.", "is_rest": True}), 200

    # If there are logs today, keep user on that same training day.
    today_log = db.session.query(WorkoutLog).join(Exercise).join(SplitDay).filter(
        WorkoutLog.user_id == user_id,
        WorkoutLog.date == date.today(),
        SplitDay.split_id == active_split.id
    ).order_by(WorkoutLog.logged_at.desc()).first()

    selected_day = None
    if today_log:
        selected_day = today_log.exercise.split_day

    if not selected_day:
        # Otherwise, move to the next training day after the most recently logged day.
        last_log = db.session.query(WorkoutLog).join(Exercise).join(SplitDay).filter(
            WorkoutLog.user_id == user_id,
            SplitDay.split_id == active_split.id
        ).order_by(WorkoutLog.date.desc(), WorkoutLog.logged_at.desc()).first()

        if not last_log:
            selected_day = training_days[0]
        else:
            last_day_id = last_log.exercise.split_day.id
            current_idx = next((i for i, d in enumerate(training_days) if d.id == last_day_id), None)
            if current_idx is None:
                selected_day = training_days[0]
            else:
                selected_day = training_days[(current_idx + 1) % len(training_days)]

    # For each exercise in the selected training day, attach today's logs.
    exercises_with_logs = []
    for exercise in selected_day.exercises:
        logs_today = WorkoutLog.query.filter_by(
            user_id=user_id,
            exercise_id=exercise.id,
            date=date.today()
        ).order_by(WorkoutLog.set_number).all()

        exercises_with_logs.append({
            **exercise.to_dict(),
            "logged_sets": [l.to_dict() for l in logs_today]
        })

    return jsonify({
        "is_rest": False,
        "split_name": active_split.name,
        "day_name": selected_day.day_name,
        "day_label": selected_day.day_label,
        "day_id": selected_day.id,
        "exercises": exercises_with_logs
    }), 200


# ─── GET LOGS FOR A SPECIFIC DATE ─────────────────────────────────────────────

@logs_bp.route("/date/<string:log_date>", methods=["GET"])
@jwt_required()
def get_logs_by_date(log_date):
    """Get all workout logs for a specific date. e.g. /logs/date/2025-01-15"""
    user_id = int(get_jwt_identity())

    try:
        parsed_date = date.fromisoformat(log_date)
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    logs = WorkoutLog.query.filter_by(
        user_id=user_id,
        date=parsed_date
    ).order_by(WorkoutLog.exercise_id, WorkoutLog.set_number).all()

    # Group logs by exercise
    grouped = {}
    for log in logs:
        ex_id = log.exercise_id
        if ex_id not in grouped:
            grouped[ex_id] = {
                "exercise_id": ex_id,
                "exercise_name": log.exercise.name,
                "muscle_group": log.exercise.muscle_group,
                "sets": []
            }
        grouped[ex_id]["sets"].append(log.to_dict())

    return jsonify({
        "date": log_date,
        "exercises": list(grouped.values())
    }), 200


# ─── GET HISTORY FOR ONE EXERCISE ─────────────────────────────────────────────

@logs_bp.route("/exercise/<int:exercise_id>", methods=["GET"])
@jwt_required()
def get_exercise_history(exercise_id):
    """
    Get full log history for one exercise.
    Used for progress tracking: "last time I did bench press I lifted X"
    """
    user_id = int(get_jwt_identity())

    exercise = Exercise.query.get(exercise_id)
    if not exercise or exercise.split_day.split.user_id != user_id:
        return jsonify({"error": "Exercise not found"}), 404

    logs = WorkoutLog.query.filter_by(
        user_id=user_id,
        exercise_id=exercise_id
    ).order_by(WorkoutLog.date.desc(), WorkoutLog.set_number).all()

    # Group by date
    grouped = {}
    for log in logs:
        d = log.date.isoformat()
        if d not in grouped:
            grouped[d] = {"date": d, "sets": []}
        grouped[d]["sets"].append(log.to_dict())

    return jsonify({
        "exercise": exercise.to_dict(),
        "history": list(grouped.values())
    }), 200


# ─── DELETE A LOG ENTRY ───────────────────────────────────────────────────────

@logs_bp.route("/<int:log_id>", methods=["DELETE"])
@jwt_required()
def delete_log(log_id):
    user_id = int(get_jwt_identity())
    log = WorkoutLog.query.filter_by(id=log_id, user_id=user_id).first()

    if not log:
        return jsonify({"error": "Log not found"}), 404

    db.session.delete(log)
    db.session.commit()

    return jsonify({"message": "Log deleted"}), 200


# ─── EDIT A LOG ENTRY ────────────────────────────────────────────────────────

@logs_bp.route("/<int:log_id>", methods=["PATCH"])
@jwt_required()
def edit_log(log_id):
    """Edit reps/weight/notes on an existing log entry."""
    user_id = int(get_jwt_identity())
    log = WorkoutLog.query.filter_by(id=log_id, user_id=user_id).first()

    if not log:
        return jsonify({"error": "Log not found"}), 404

    data = request.get_json()

    if "reps" in data:
        log.reps = data["reps"]
    if "weight" in data:
        log.weight = data["weight"]
    if "notes" in data:
        log.notes = data["notes"]

    db.session.commit()

    return jsonify({"message": "Log updated", "log": log.to_dict()}), 200


@logs_bp.route("/analytics", methods=["GET"])
@jwt_required()
def analytics():
    user_id = int(get_jwt_identity())
    today = date.today()
    dates_14 = [today - timedelta(days=i) for i in range(13, -1, -1)]
    dates_7 = dates_14[-7:]
    date_keys_14 = [d.isoformat() for d in dates_14]
    date_keys_7 = [d.isoformat() for d in dates_7]

    all_logs = db.session.query(WorkoutLog).join(Exercise).filter(
        WorkoutLog.user_id == user_id
    ).all()

    exercise_max_score = defaultdict(float)
    for log in all_logs:
        raw_score = (float(log.weight or 0) * float(log.reps or 0)) * intensity_factor_for_reps(log.reps)
        exercise_max_score[log.exercise_id] = max(exercise_max_score[log.exercise_id], raw_score)

    logs_14 = [log for log in all_logs if log.date in set(dates_14)]

    day_total_raw = defaultdict(float)
    day_total_sets = defaultdict(int)
    muscle_daily_raw = {muscle: defaultdict(float) for muscle in TRACKED_MUSCLES}

    for log in logs_14:
        raw_score = (float(log.weight or 0) * float(log.reps or 0)) * intensity_factor_for_reps(log.reps)
        max_for_exercise = exercise_max_score.get(log.exercise_id, 0.0)
        normalizer = max(max_for_exercise, raw_score, 1.0)
        normalized_score = raw_score / normalizer
        distribution = get_distribution_for_exercise(log.exercise.name, log.exercise.muscle_group)

        day_key = log.date.isoformat()
        day_total_raw[day_key] += normalized_score
        day_total_sets[day_key] += 1

        for muscle, share in distribution.items():
            if muscle in muscle_daily_raw:
                muscle_daily_raw[muscle][day_key] += normalized_score * float(share)

    def apply_decay(series_by_day):
        values = []
        previous = 0.0
        for day_key in date_keys_14:
            current = series_by_day.get(day_key, 0.0)
            if current > 0:
                previous = current
            else:
                previous *= 0.98
            values.append(previous)
        return values

    def rolling_avg(values, window=7):
        result = []
        for idx in range(len(values)):
            start = max(0, idx - window + 1)
            segment = values[start:idx + 1]
            result.append(sum(segment) / max(len(segment), 1))
        return result

    def pct_growth(prev, curr):
        if prev <= 0 and curr <= 0:
            return 0.0
        if prev <= 0:
            return 100.0
        return ((curr - prev) / prev) * 100.0

    muscles_payload = {}
    latest_week_avg_total = 0.0
    prev_week_avg_total = 0.0

    for muscle in TRACKED_MUSCLES:
        decayed = apply_decay(muscle_daily_raw[muscle])
        smoothed = rolling_avg(decayed, window=7)
        prev_week_avg = sum(smoothed[:7]) / 7 if smoothed[:7] else 0.0
        current_week_avg = sum(smoothed[7:14]) / 7 if smoothed[7:14] else 0.0
        growth = pct_growth(prev_week_avg, current_week_avg)

        latest_week_avg_total += current_week_avg
        prev_week_avg_total += prev_week_avg

        muscles_payload[muscle] = {
            "growth": round(growth, 1),
            "trend": [round(v, 4) for v in smoothed],
            "week_delta": round(current_week_avg - prev_week_avg, 4),
        }

    weekly_raw_with_decay = apply_decay(day_total_raw)
    weekly_smoothed = rolling_avg(weekly_raw_with_decay, window=7)
    weekly_load = [
        {"date": day_key, "score": round(weekly_smoothed[idx], 4)}
        for idx, day_key in enumerate(date_keys_7, start=7)
    ]

    training_days = sum(1 for day_key in date_keys_14 if day_total_sets[day_key] > 0)
    total_sets = sum(day_total_sets[day_key] for day_key in date_keys_14)
    consistency_score = (training_days / 14) * 100
    strength_trend = pct_growth(prev_week_avg_total, latest_week_avg_total)

    return jsonify({
        "snapshot": {
            "training_days": training_days,
            "total_sets": total_sets,
            "consistency_score": round(consistency_score, 1),
            "strength_trend": round(strength_trend, 1),
        },
        "muscles": muscles_payload,
        "weekly_load": weekly_load,
    }), 200
