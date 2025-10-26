from __future__ import annotations

import io
import os
from datetime import datetime
from functools import wraps
from pathlib import Path

import pandas as pd
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from . import db
from .models import Admin, Experiment, ReportSubmission, Student
from .services import annotate_report, evaluate_report


ALLOWED_EXTENSIONS = {"docx"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(role: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if session.get("role") != role:
                flash("请先登录", "warning")
                if role == "admin":
                    return redirect(url_for("auth.admin_login"))
                return redirect(url_for("auth.student_login"))
            return func(*args, **kwargs)

        return wrapper

    return decorator


def init_default_admin() -> None:
    if not Admin.query.filter_by(username="admin").first():
        admin = Admin(username="admin")
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()


auth_bp = Blueprint("auth", __name__)
admin_bp = Blueprint("admin", __name__)
student_bp = Blueprint("student", __name__)


@auth_bp.before_app_request
def ensure_admin_exists() -> None:
    if Admin.query.count() == 0:
        init_default_admin()


@auth_bp.route("/")
def index():
    return render_template("index.html")


@auth_bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.check_password(password):
            session.clear()
            session["role"] = "admin"
            session["admin_id"] = admin.id
            flash("管理员登录成功", "success")
            return redirect(url_for("admin.dashboard"))
        flash("用户名或密码错误", "danger")
    return render_template("admin_login.html")


@auth_bp.route("/student/login", methods=["GET", "POST"])
def student_login():
    if request.method == "POST":
        student_number = request.form.get("student_number", "").strip()
        password = request.form.get("password", "")
        student = Student.query.filter_by(student_number=student_number).first()
        if student and student.check_password(password):
            session.clear()
            session["role"] = "student"
            session["student_id"] = student.id
            flash("登录成功", "success")
            return redirect(url_for("student.dashboard"))
        flash("学号或密码错误", "danger")
    return render_template("student_login.html")


@auth_bp.route("/logout")
def logout():
    role = session.pop("role", None)
    session.clear()
    if role == "admin":
        flash("已退出管理员账号", "info")
        return redirect(url_for("auth.admin_login"))
    flash("已退出登录", "info")
    return redirect(url_for("auth.student_login"))


@admin_bp.route("/dashboard")
@login_required("admin")
def dashboard():
    experiments = Experiment.query.order_by(Experiment.id).all()
    student_count = Student.query.count()
    submission_counts = {
        exp.id: ReportSubmission.query.filter_by(experiment_id=exp.id).count() for exp in experiments
    }
    students = Student.query.order_by(Student.student_number).all()
    return render_template(
        "admin_dashboard.html",
        experiments=experiments,
        student_count=student_count,
        submission_counts=submission_counts,
        students=students,
    )


@admin_bp.route("/experiments", methods=["POST"])
@login_required("admin")
def create_experiment():
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    if not name:
        flash("实验名称不能为空", "warning")
    else:
        experiment = Experiment(name=name, description=description)
        db.session.add(experiment)
        db.session.commit()
        flash("实验创建成功", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/students/import", methods=["POST"])
@login_required("admin")
def import_students():
    file = request.files.get("file")
    if file is None or file.filename == "":
        flash("请上传Excel文件", "warning")
        return redirect(url_for("admin.dashboard"))
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        flash("仅支持Excel文件", "warning")
        return redirect(url_for("admin.dashboard"))

    try:
        df = pd.read_excel(file)
        df.columns = [str(col).strip().lower() for col in df.columns]
    except Exception as exc:  # noqa: BLE001
        flash(f"读取Excel失败: {exc}", "danger")
        return redirect(url_for("admin.dashboard"))

    required_columns = {"student_number", "name", "password"}
    if not required_columns.issubset(set(df.columns)):
        flash("Excel需包含 student_number、name、password 列", "danger")
        return redirect(url_for("admin.dashboard"))

    created = 0
    updated = 0
    for _, row in df.iterrows():
        student_number = str(row.get("student_number", "")).strip()
        name = str(row.get("name", "")).strip()
        password = str(row.get("password", "")).strip()
        if not student_number or not name or not password:
            continue
        student = Student.query.filter_by(student_number=student_number).first()
        if student:
            student.name = name
            student.set_password(password)
            updated += 1
        else:
            student = Student(student_number=student_number, name=name)
            student.set_password(password)
            db.session.add(student)
            created += 1
    db.session.commit()
    flash(f"成功导入学生：新增 {created} 人，更新 {updated} 人", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/students/<int:student_id>/update", methods=["POST"])
@login_required("admin")
def update_student(student_id: int):
    student = Student.query.get_or_404(student_id)
    name = request.form.get("name", "").strip()
    password = request.form.get("password", "").strip()
    if not name:
        flash("学生姓名不能为空", "warning")
        return redirect(url_for("admin.dashboard"))
    student.name = name
    if password:
        student.set_password(password)
    db.session.commit()
    flash("学生信息已更新", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/password", methods=["GET", "POST"], endpoint="change_password")
@login_required("admin")
def admin_change_password():
    admin = Admin.query.get_or_404(session.get("admin_id"))
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not admin.check_password(current_password):
            flash("当前密码错误", "danger")
        elif not new_password:
            flash("新密码不能为空", "warning")
        elif new_password != confirm_password:
            flash("两次输入的新密码不一致", "warning")
        else:
            admin.set_password(new_password)
            db.session.commit()
            flash("密码修改成功", "success")
            return redirect(url_for("admin.dashboard"))

    return render_template(
        "change_password.html",
        title="修改管理员密码",
        heading="修改管理员密码",
        submit_text="更新密码",
    )


@admin_bp.route("/summary")
@login_required("admin")
def submissions_summary():
    experiments = Experiment.query.order_by(Experiment.id).all()
    students = Student.query.order_by(Student.student_number).all()
    submissions = ReportSubmission.query.all()
    submission_map = {(sub.student_id, sub.experiment_id): sub for sub in submissions}

    rows = []
    for student in students:
        cells = []
        scores: list[float] = []
        for experiment in experiments:
            submission = submission_map.get((student.id, experiment.id))
            cells.append(submission)
            if submission and submission.score is not None:
                scores.append(submission.score)
        avg_score = round(sum(scores) / len(scores), 2) if scores else None
        completed = sum(1 for submission in cells if submission is not None)
        rows.append(
            {
                "student": student,
                "cells": cells,
                "avg_score": avg_score,
                "completed": completed,
            }
        )

    return render_template(
        "submission_summary.html",
        experiments=experiments,
        rows=rows,
    )


@admin_bp.route("/experiments/<int:experiment_id>/export")
@login_required("admin")
def export_results(experiment_id: int):
    experiment = Experiment.query.get_or_404(experiment_id)
    submissions = (
        ReportSubmission.query.filter_by(experiment_id=experiment_id)
        .join(Student)
        .order_by(ReportSubmission.submitted_at.desc())
        .all()
    )

    data = [
        {
            "student_number": submission.student.student_number,
            "name": submission.student.name,
            "score": submission.score,
            "feedback": submission.feedback,
            "submitted_at": submission.submitted_at.strftime("%Y-%m-%d %H:%M"),
        }
        for submission in submissions
    ]
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=experiment.name[:31] or "Sheet1")
    output.seek(0)
    filename = f"{experiment.name}_成绩统计.xlsx"
    return send_file(output, as_attachment=True, download_name=filename)


@student_bp.route("/dashboard")
@login_required("student")
def dashboard():
    student_id = session.get("student_id")
    student = Student.query.get_or_404(student_id)
    experiments = Experiment.query.order_by(Experiment.id).all()
    submissions = {sub.experiment_id: sub for sub in student.submissions}
    return render_template(
        "student_dashboard.html",
        student=student,
        experiments=experiments,
        submissions=submissions,
    )


@student_bp.route("/submit/<int:experiment_id>", methods=["GET", "POST"])
@login_required("student")
def submit_report(experiment_id: int):
    experiment = Experiment.query.get_or_404(experiment_id)
    student = Student.query.get_or_404(session["student_id"])
    submission = ReportSubmission.query.filter_by(
        student_id=student.id, experiment_id=experiment_id
    ).first()

    if request.method == "POST":
        file: FileStorage | None = request.files.get("file")
        if file is None or file.filename == "":
            flash("请上传Word实验报告", "warning")
            return redirect(request.url)
        if not allowed_file(file.filename):
            flash("仅支持.docx文件", "warning")
            return redirect(request.url)

        filename = secure_filename(file.filename)
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        stored_name = f"{student.student_number}_{experiment_id}_{timestamp}_{filename}"
        upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
        stored_path = upload_folder / stored_name
        file.save(stored_path)

        score, feedback = evaluate_report(stored_path)
        processed_path = annotate_report(
            stored_path,
            score,
            feedback,
            Path(current_app.config["PROCESSED_FOLDER"]) / stored_name,
        )

        if submission is None:
            submission = ReportSubmission(
                student_id=student.id,
                experiment_id=experiment_id,
                original_filename=filename,
                stored_path=str(stored_path),
                processed_path=str(processed_path),
                score=score,
                feedback=feedback,
            )
            db.session.add(submission)
        else:
            submission.original_filename = filename
            submission.stored_path = str(stored_path)
            submission.processed_path = str(processed_path)
            submission.score = score
            submission.feedback = feedback
            submission.submitted_at = datetime.utcnow()

        db.session.commit()
        flash("实验报告提交成功", "success")
        return redirect(url_for("student.dashboard"))

    return render_template("submit_report.html", experiment=experiment, submission=submission)


@student_bp.route("/password", methods=["GET", "POST"], endpoint="change_password")
@login_required("student")
def student_change_password():
    student = Student.query.get_or_404(session.get("student_id"))
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not student.check_password(current_password):
            flash("当前密码错误", "danger")
        elif not new_password:
            flash("新密码不能为空", "warning")
        elif new_password != confirm_password:
            flash("两次输入的新密码不一致", "warning")
        else:
            student.set_password(new_password)
            db.session.commit()
            flash("密码修改成功", "success")
            return redirect(url_for("student.dashboard"))

    return render_template(
        "change_password.html",
        title="修改学生密码",
        heading="修改登录密码",
        submit_text="更新密码",
    )


@student_bp.route("/download/<int:submission_id>")
@login_required("student")
def download_report(submission_id: int):
    submission = ReportSubmission.query.get_or_404(submission_id)
    if submission.student_id != session.get("student_id"):
        flash("无权访问该文件", "danger")
        return redirect(url_for("student.dashboard"))
    if not submission.processed_path or not os.path.exists(submission.processed_path):
        flash("文件不存在", "danger")
        return redirect(url_for("student.dashboard"))
    return send_file(submission.processed_path, as_attachment=True)


@admin_bp.route("/submissions/<int:submission_id>/download")
@login_required("admin")
def admin_download(submission_id: int):
    submission = ReportSubmission.query.get_or_404(submission_id)
    if not submission.processed_path or not os.path.exists(submission.processed_path):
        flash("文件不存在", "danger")
        return redirect(url_for("admin.dashboard"))
    return send_file(submission.processed_path, as_attachment=True)


@admin_bp.route("/experiments/<int:experiment_id>")
@login_required("admin")
def view_experiment(experiment_id: int):
    experiment = Experiment.query.get_or_404(experiment_id)
    submissions = (
        ReportSubmission.query.filter_by(experiment_id=experiment_id)
        .join(Student)
        .order_by(ReportSubmission.submitted_at.desc())
        .all()
    )
    return render_template(
        "experiment_detail.html",
        experiment=experiment,
        submissions=submissions,
    )
