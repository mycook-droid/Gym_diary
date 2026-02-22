from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from sqlalchemy import text

db = SQLAlchemy()
bcrypt = Bcrypt()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    photo_url = db.Column(db.String(500), nullable=True)
    motivation_note = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    splits = db.relationship("WorkoutSplit", backref="user", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "photo_url": self.photo_url,
            "motivation_note": self.motivation_note,
            "created_at": self.created_at.isoformat()
        }


def ensure_schema_updates():
    """Lightweight dev migration for newly added user profile columns."""
    table_info = db.session.execute(text("PRAGMA table_info(users)")).fetchall()
    columns = {row[1] for row in table_info}

    if "photo_url" not in columns:
        db.session.execute(text("ALTER TABLE users ADD COLUMN photo_url VARCHAR(500)"))
    if "motivation_note" not in columns:
        db.session.execute(text("ALTER TABLE users ADD COLUMN motivation_note VARCHAR(500)"))

    db.session.commit()


class WorkoutSplit(db.Model):
    """
    A split is a weekly plan. e.g. 'Push Pull Legs' or 'Bro Split'.
    One user can have multiple splits but only one active at a time.
    """
    __tablename__ = "workout_splits"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)           # e.g. "Push Pull Legs"
    is_active = db.Column(db.Boolean, default=False)           # only one active split at a time
    is_preset = db.Column(db.Boolean, default=False)           # was it from our pre-designed library?
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    days = db.relationship("SplitDay", backref="split", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "is_active": self.is_active,
            "is_preset": self.is_preset,
            "days": [day.to_dict() for day in self.days]
        }


class SplitDay(db.Model):
    """
    A single day inside a split. e.g. Monday → Push, Tuesday → Pull
    """
    __tablename__ = "split_days"

    id = db.Column(db.Integer, primary_key=True)
    split_id = db.Column(db.Integer, db.ForeignKey("workout_splits.id"), nullable=False)
    day_name = db.Column(db.String(20), nullable=False)        # "Monday", "Tuesday", etc.
    day_label = db.Column(db.String(50), nullable=False)       # "Push", "Pull", "Legs", "Rest"

    # Relationships
    exercises = db.relationship("Exercise", backref="split_day", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "day_name": self.day_name,
            "day_label": self.day_label,
            "exercises": [ex.to_dict() for ex in self.exercises]
        }


class Exercise(db.Model):
    """
    An exercise inside a split day. e.g. Bench Press inside Push day.
    This is the template — not the actual log.
    """
    __tablename__ = "exercises"

    id = db.Column(db.Integer, primary_key=True)
    split_day_id = db.Column(db.Integer, db.ForeignKey("split_days.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)            # "Bench Press"
    muscle_group = db.Column(db.String(50), nullable=True)      # "Chest", "Back", "Legs"
    default_sets = db.Column(db.Integer, default=3)             # suggested sets
    order_index = db.Column(db.Integer, default=0)              # display order in the list

    # Relationships
    logs = db.relationship("WorkoutLog", backref="exercise", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "muscle_group": self.muscle_group,
            "default_sets": self.default_sets,
            "order_index": self.order_index
        }


class WorkoutLog(db.Model):
    """
    The actual workout entry. When user logs a set in the gym, it goes here.
    One row = one set of one exercise on one date.
    """
    __tablename__ = "workout_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey("exercises.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)                   # the gym session date
    set_number = db.Column(db.Integer, nullable=False)          # set 1, set 2, set 3
    reps = db.Column(db.Integer, nullable=False)
    weight = db.Column(db.Float, nullable=False)                # in kg
    notes = db.Column(db.String(200), nullable=True)            # optional note per set
    logged_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "exercise_id": self.exercise_id,
            "exercise_name": self.exercise.name if self.exercise else None,
            "date": self.date.isoformat(),
            "set_number": self.set_number,
            "reps": self.reps,
            "weight": self.weight,
            "notes": self.notes
        }
