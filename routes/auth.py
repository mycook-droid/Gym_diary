from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models import db, User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/check-username", methods=["GET"])
def check_username():
    username = (request.args.get("username") or "").strip().lower()
    if not username:
        return jsonify({"available": False, "message": "Username is required"}), 400

    existing = User.query.filter_by(username=username).first()
    return jsonify({"available": existing is None}), 200


@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()

    # Validate required fields
    required = ["username", "email", "password"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400

    # Check if user already exists
    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already registered"}), 409

    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "Username already taken"}), 409

    # Create user
    user = User(
        username=data["username"].strip().lower(),
        email=data["email"].strip().lower()
    )
    user.set_password(data["password"])

    db.session.add(user)
    db.session.commit()

    # Generate token right after signup so user is logged in immediately
    token = create_access_token(identity=str(user.id))

    return jsonify({
        "message": "Account created successfully",
        "token": token,
        "user": user.to_dict()
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    username = (data.get("username") or "").strip().lower()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")

    if not password or (not username and not email):
        return jsonify({"error": "Username and password are required"}), 400

    # Prefer username login, keep email fallback for compatibility.
    user = None
    if username:
        user = User.query.filter_by(username=username).first()
    if not user and email:
        user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid username/email or password"}), 401

    token = create_access_token(identity=str(user.id))

    return jsonify({
        "message": "Login successful",
        "token": token,
        "user": user.to_dict()
    }), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_me():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({"user": user.to_dict()}), 200


@auth_bp.route("/me", methods=["PATCH"])
@jwt_required()
def update_me():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json() or {}

    if "username" in data:
        new_username = (data["username"] or "").strip().lower()
        if not new_username:
            return jsonify({"error": "Username cannot be empty"}), 400
        existing = User.query.filter_by(username=new_username).first()
        if existing and existing.id != user.id:
            return jsonify({"error": "Username already taken"}), 409
        user.username = new_username

    if "email" in data:
        new_email = (data["email"] or "").strip().lower()
        if not new_email:
            return jsonify({"error": "Email cannot be empty"}), 400
        existing = User.query.filter_by(email=new_email).first()
        if existing and existing.id != user.id:
            return jsonify({"error": "Email already registered"}), 409
        user.email = new_email

    if "password" in data and data["password"]:
        user.set_password(data["password"])

    if "photo_url" in data:
        user.photo_url = (data["photo_url"] or "").strip() or None

    if "motivation_note" in data:
        note = (data["motivation_note"] or "").strip()
        user.motivation_note = note[:500] if note else None

    db.session.commit()
    return jsonify({"message": "Profile updated", "user": user.to_dict()}), 200
