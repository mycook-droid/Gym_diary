from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, WorkoutLog, Exercise, WorkoutSplit, SplitDay
from datetime import date, datetime

logs_bp = Blueprint("logs", __name__)


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
