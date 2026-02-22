from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, WorkoutSplit, SplitDay, Exercise

splits_bp = Blueprint("splits", __name__)


# ─── PRESET SPLITS LIBRARY ───────────────────────────────────────────────────

PRESET_SPLITS = {
    "ppl": {
        "name": "Push Pull Legs",
        "days": [
            {
                "day_name": "Monday",
                "day_label": "Push",
                "exercises": [
                    {"name": "Bench Press", "muscle_group": "Chest", "default_sets": 3},
                    {"name": "Incline Dumbbell Press", "muscle_group": "Chest", "default_sets": 3},
                    {"name": "Overhead Press", "muscle_group": "Shoulders", "default_sets": 3},
                    {"name": "Lateral Raises", "muscle_group": "Shoulders", "default_sets": 3},
                    {"name": "Tricep Pushdown", "muscle_group": "Triceps", "default_sets": 3},
                    {"name": "Overhead Tricep Extension", "muscle_group": "Triceps", "default_sets": 3},
                ]
            },
            {
                "day_name": "Tuesday",
                "day_label": "Pull",
                "exercises": [
                    {"name": "Deadlift", "muscle_group": "Back", "default_sets": 4},
                    {"name": "Pull Ups", "muscle_group": "Back", "default_sets": 3},
                    {"name": "Barbell Row", "muscle_group": "Back", "default_sets": 3},
                    {"name": "Face Pulls", "muscle_group": "Rear Delts", "default_sets": 3},
                    {"name": "Barbell Curl", "muscle_group": "Biceps", "default_sets": 3},
                    {"name": "Hammer Curl", "muscle_group": "Biceps", "default_sets": 3},
                ]
            },
            {
                "day_name": "Wednesday",
                "day_label": "Legs",
                "exercises": [
                    {"name": "Squat", "muscle_group": "Quads", "default_sets": 4},
                    {"name": "Romanian Deadlift", "muscle_group": "Hamstrings", "default_sets": 3},
                    {"name": "Leg Press", "muscle_group": "Quads", "default_sets": 3},
                    {"name": "Leg Curl", "muscle_group": "Hamstrings", "default_sets": 3},
                    {"name": "Calf Raises", "muscle_group": "Calves", "default_sets": 4},
                ]
            },
            {"day_name": "Thursday", "day_label": "Rest", "exercises": []},
            {
                "day_name": "Friday",
                "day_label": "Push",
                "exercises": [
                    {"name": "Bench Press", "muscle_group": "Chest", "default_sets": 4},
                    {"name": "Cable Fly", "muscle_group": "Chest", "default_sets": 3},
                    {"name": "Overhead Press", "muscle_group": "Shoulders", "default_sets": 3},
                    {"name": "Lateral Raises", "muscle_group": "Shoulders", "default_sets": 3},
                    {"name": "Skull Crushers", "muscle_group": "Triceps", "default_sets": 3},
                ]
            },
            {
                "day_name": "Saturday",
                "day_label": "Pull",
                "exercises": [
                    {"name": "Pull Ups", "muscle_group": "Back", "default_sets": 4},
                    {"name": "Seated Cable Row", "muscle_group": "Back", "default_sets": 3},
                    {"name": "Lat Pulldown", "muscle_group": "Back", "default_sets": 3},
                    {"name": "Barbell Curl", "muscle_group": "Biceps", "default_sets": 3},
                    {"name": "Incline Dumbbell Curl", "muscle_group": "Biceps", "default_sets": 3},
                ]
            },
            {"day_name": "Sunday", "day_label": "Rest", "exercises": []},
        ]
    },
    "upper_lower": {
        "name": "Upper Lower Split",
        "days": [
            {
                "day_name": "Monday",
                "day_label": "Upper",
                "exercises": [
                    {"name": "Bench Press", "muscle_group": "Chest", "default_sets": 4},
                    {"name": "Barbell Row", "muscle_group": "Back", "default_sets": 4},
                    {"name": "Overhead Press", "muscle_group": "Shoulders", "default_sets": 3},
                    {"name": "Pull Ups", "muscle_group": "Back", "default_sets": 3},
                    {"name": "Barbell Curl", "muscle_group": "Biceps", "default_sets": 3},
                    {"name": "Tricep Pushdown", "muscle_group": "Triceps", "default_sets": 3},
                ]
            },
            {
                "day_name": "Tuesday",
                "day_label": "Lower",
                "exercises": [
                    {"name": "Squat", "muscle_group": "Quads", "default_sets": 4},
                    {"name": "Romanian Deadlift", "muscle_group": "Hamstrings", "default_sets": 3},
                    {"name": "Leg Press", "muscle_group": "Quads", "default_sets": 3},
                    {"name": "Leg Curl", "muscle_group": "Hamstrings", "default_sets": 3},
                    {"name": "Calf Raises", "muscle_group": "Calves", "default_sets": 4},
                ]
            },
            {"day_name": "Wednesday", "day_label": "Rest", "exercises": []},
            {
                "day_name": "Thursday",
                "day_label": "Upper",
                "exercises": [
                    {"name": "Incline Bench Press", "muscle_group": "Chest", "default_sets": 4},
                    {"name": "Seated Cable Row", "muscle_group": "Back", "default_sets": 4},
                    {"name": "Lateral Raises", "muscle_group": "Shoulders", "default_sets": 3},
                    {"name": "Lat Pulldown", "muscle_group": "Back", "default_sets": 3},
                    {"name": "Hammer Curl", "muscle_group": "Biceps", "default_sets": 3},
                    {"name": "Skull Crushers", "muscle_group": "Triceps", "default_sets": 3},
                ]
            },
            {
                "day_name": "Friday",
                "day_label": "Lower",
                "exercises": [
                    {"name": "Deadlift", "muscle_group": "Back", "default_sets": 4},
                    {"name": "Leg Press", "muscle_group": "Quads", "default_sets": 4},
                    {"name": "Bulgarian Split Squat", "muscle_group": "Quads", "default_sets": 3},
                    {"name": "Leg Curl", "muscle_group": "Hamstrings", "default_sets": 3},
                    {"name": "Calf Raises", "muscle_group": "Calves", "default_sets": 4},
                ]
            },
            {"day_name": "Saturday", "day_label": "Rest", "exercises": []},
            {"day_name": "Sunday", "day_label": "Rest", "exercises": []},
        ]
    },
    "bro_split": {
        "name": "Bro Split",
        "days": [
            {
                "day_name": "Monday",
                "day_label": "Chest",
                "exercises": [
                    {"name": "Bench Press", "muscle_group": "Chest", "default_sets": 4},
                    {"name": "Incline Dumbbell Press", "muscle_group": "Chest", "default_sets": 3},
                    {"name": "Cable Fly", "muscle_group": "Chest", "default_sets": 3},
                    {"name": "Dips", "muscle_group": "Chest", "default_sets": 3},
                ]
            },
            {
                "day_name": "Tuesday",
                "day_label": "Back",
                "exercises": [
                    {"name": "Deadlift", "muscle_group": "Back", "default_sets": 4},
                    {"name": "Pull Ups", "muscle_group": "Back", "default_sets": 3},
                    {"name": "Barbell Row", "muscle_group": "Back", "default_sets": 3},
                    {"name": "Lat Pulldown", "muscle_group": "Back", "default_sets": 3},
                    {"name": "Seated Cable Row", "muscle_group": "Back", "default_sets": 3},
                ]
            },
            {
                "day_name": "Wednesday",
                "day_label": "Shoulders",
                "exercises": [
                    {"name": "Overhead Press", "muscle_group": "Shoulders", "default_sets": 4},
                    {"name": "Lateral Raises", "muscle_group": "Shoulders", "default_sets": 4},
                    {"name": "Front Raises", "muscle_group": "Shoulders", "default_sets": 3},
                    {"name": "Face Pulls", "muscle_group": "Rear Delts", "default_sets": 3},
                ]
            },
            {
                "day_name": "Thursday",
                "day_label": "Arms",
                "exercises": [
                    {"name": "Barbell Curl", "muscle_group": "Biceps", "default_sets": 4},
                    {"name": "Hammer Curl", "muscle_group": "Biceps", "default_sets": 3},
                    {"name": "Incline Dumbbell Curl", "muscle_group": "Biceps", "default_sets": 3},
                    {"name": "Tricep Pushdown", "muscle_group": "Triceps", "default_sets": 4},
                    {"name": "Skull Crushers", "muscle_group": "Triceps", "default_sets": 3},
                    {"name": "Overhead Tricep Extension", "muscle_group": "Triceps", "default_sets": 3},
                ]
            },
            {
                "day_name": "Friday",
                "day_label": "Legs",
                "exercises": [
                    {"name": "Squat", "muscle_group": "Quads", "default_sets": 4},
                    {"name": "Romanian Deadlift", "muscle_group": "Hamstrings", "default_sets": 3},
                    {"name": "Leg Press", "muscle_group": "Quads", "default_sets": 3},
                    {"name": "Leg Curl", "muscle_group": "Hamstrings", "default_sets": 3},
                    {"name": "Calf Raises", "muscle_group": "Calves", "default_sets": 4},
                ]
            },
            {"day_name": "Saturday", "day_label": "Rest", "exercises": []},
            {"day_name": "Sunday", "day_label": "Rest", "exercises": []},
        ]
    }
}


# ─── HELPER ──────────────────────────────────────────────────────────────────

def build_split_from_data(user_id, split_data, is_preset=False):
    """Creates a WorkoutSplit with all its days and exercises from a dict."""
    split = WorkoutSplit(
        user_id=user_id,
        name=split_data["name"],
        is_preset=is_preset,
        is_active=False
    )
    db.session.add(split)
    db.session.flush()  # get split.id without committing

    for order, day_data in enumerate(split_data["days"]):
        day = SplitDay(
            split_id=split.id,
            day_name=day_data["day_name"],
            day_label=day_data["day_label"]
        )
        db.session.add(day)
        db.session.flush()

        for idx, ex_data in enumerate(day_data.get("exercises", [])):
            exercise = Exercise(
                split_day_id=day.id,
                name=ex_data["name"],
                muscle_group=ex_data.get("muscle_group"),
                default_sets=ex_data.get("default_sets", 3),
                order_index=idx
            )
            db.session.add(exercise)

    return split


# ─── ROUTES ──────────────────────────────────────────────────────────────────

@splits_bp.route("/presets", methods=["GET"])
def get_presets():
    """List all available preset splits (no auth needed, it's public info)."""
    presets = [
        {"key": key, "name": val["name"]}
        for key, val in PRESET_SPLITS.items()
    ]
    return jsonify({"presets": presets}), 200


@splits_bp.route("/presets/<preset_key>", methods=["POST"])
@jwt_required()
def use_preset(preset_key):
    """User picks a preset — we copy it into their account."""
    user_id = get_jwt_identity()

    if preset_key not in PRESET_SPLITS:
        return jsonify({"error": "Preset not found"}), 404

    split = build_split_from_data(user_id, PRESET_SPLITS[preset_key], is_preset=True)
    db.session.commit()

    return jsonify({
        "message": f"{split.name} added to your splits",
        "split": split.to_dict()
    }), 201


@splits_bp.route("/", methods=["POST"])
@jwt_required()
def create_custom_split():
    """User creates a fully custom split."""
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data.get("name"):
        return jsonify({"error": "Split name is required"}), 400

    if not data.get("days") or len(data["days"]) == 0:
        return jsonify({"error": "At least one day is required"}), 400

    split = build_split_from_data(user_id, data, is_preset=False)
    db.session.commit()

    return jsonify({
        "message": "Custom split created",
        "split": split.to_dict()
    }), 201


@splits_bp.route("/", methods=["GET"])
@jwt_required()
def get_my_splits():
    """Get all splits belonging to the logged-in user."""
    user_id = get_jwt_identity()
    splits = WorkoutSplit.query.filter_by(user_id=user_id).all()
    return jsonify({"splits": [s.to_dict() for s in splits]}), 200


@splits_bp.route("/<int:split_id>", methods=["GET"])
@jwt_required()
def get_split(split_id):
    user_id = get_jwt_identity()
    split = WorkoutSplit.query.filter_by(id=split_id, user_id=user_id).first()

    if not split:
        return jsonify({"error": "Split not found"}), 404

    return jsonify({"split": split.to_dict()}), 200


@splits_bp.route("/<int:split_id>/activate", methods=["PATCH"])
@jwt_required()
def activate_split(split_id):
    """Set one split as active. Deactivates all others."""
    user_id = get_jwt_identity()

    # Deactivate all user's splits first
    WorkoutSplit.query.filter_by(user_id=user_id).update({"is_active": False})

    split = WorkoutSplit.query.filter_by(id=split_id, user_id=user_id).first()
    if not split:
        return jsonify({"error": "Split not found"}), 404

    split.is_active = True
    db.session.commit()

    return jsonify({"message": f"{split.name} is now your active split"}), 200


@splits_bp.route("/<int:split_id>", methods=["DELETE"])
@jwt_required()
def delete_split(split_id):
    user_id = get_jwt_identity()
    split = WorkoutSplit.query.filter_by(id=split_id, user_id=user_id).first()

    if not split:
        return jsonify({"error": "Split not found"}), 404

    db.session.delete(split)
    db.session.commit()

    return jsonify({"message": "Split deleted"}), 200


# ─── EXERCISE MANAGEMENT ─────────────────────────────────────────────────────

@splits_bp.route("/days/<int:day_id>/exercises", methods=["POST"])
@jwt_required()
def add_exercise(day_id):
    """Add a new exercise to a specific day."""
    user_id = get_jwt_identity()
    data = request.get_json()

    day = SplitDay.query.get(day_id)
    if not day or day.split.user_id != int(user_id):
        return jsonify({"error": "Day not found"}), 404

    if not data.get("name"):
        return jsonify({"error": "Exercise name is required"}), 400

    # Put it at the end
    last_order = db.session.query(db.func.max(Exercise.order_index))\
        .filter_by(split_day_id=day_id).scalar() or 0

    exercise = Exercise(
        split_day_id=day_id,
        name=data["name"],
        muscle_group=data.get("muscle_group"),
        default_sets=data.get("default_sets", 3),
        order_index=last_order + 1
    )
    db.session.add(exercise)
    db.session.commit()

    return jsonify({"message": "Exercise added", "exercise": exercise.to_dict()}), 201


@splits_bp.route("/exercises/<int:exercise_id>", methods=["DELETE"])
@jwt_required()
def delete_exercise(exercise_id):
    user_id = get_jwt_identity()
    exercise = Exercise.query.get(exercise_id)

    if not exercise or exercise.split_day.split.user_id != int(user_id):
        return jsonify({"error": "Exercise not found"}), 404

    db.session.delete(exercise)
    db.session.commit()

    return jsonify({"message": "Exercise deleted"}), 200