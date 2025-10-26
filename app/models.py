from __future__ import annotations

from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from . import db


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_number = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    submissions = db.relationship("ReportSubmission", back_populates="student", cascade="all, delete")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Experiment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)

    submissions = db.relationship("ReportSubmission", back_populates="experiment", cascade="all, delete")


class ReportSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    experiment_id = db.Column(db.Integer, db.ForeignKey("experiment.id"), nullable=False)
    original_filename = db.Column(db.String(256), nullable=False)
    stored_path = db.Column(db.String(256), nullable=False)
    processed_path = db.Column(db.String(256), nullable=True)
    score = db.Column(db.Float, nullable=True)
    feedback = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    student = db.relationship("Student", back_populates="submissions")
    experiment = db.relationship("Experiment", back_populates="submissions")

    __table_args__ = (db.UniqueConstraint("student_id", "experiment_id", name="uq_student_experiment"),)
