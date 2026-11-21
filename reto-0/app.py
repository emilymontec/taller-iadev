import os
import secrets
from datetime import UTC, datetime

from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import BooleanField, PasswordField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, ValidationError

load_dotenv()

db = SQLAlchemy()
csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message = "Inicia sesión para continuar."
login_manager.login_message_category = "info"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    tasks = db.relationship("Task", backref="owner", cascade="all, delete-orphan", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    completed = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)


class RegistrationForm(FlaskForm):
    username = StringField("Nombre de usuario", validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField("Contraseña", validators=[DataRequired(), Length(min=8, max=128)])
    submit = SubmitField("Crear cuenta")

    def validate_username(self, field):
        if db.session.scalar(select(User).where(User.username == field.data.strip())):
            raise ValidationError("Ese nombre de usuario ya está en uso.")


class LoginForm(FlaskForm):
    username = StringField("Nombre de usuario", validators=[DataRequired(), Length(max=80)])
    password = PasswordField("Contraseña", validators=[DataRequired(), Length(max=128)])
    submit = SubmitField("Iniciar sesión")


class TaskForm(FlaskForm):
    title = StringField("Título", validators=[DataRequired(), Length(max=160)])
    description = TextAreaField("Descripción", validators=[Length(max=4000)])
    completed = BooleanField("Marcar como completada")
    submit = SubmitField("Guardar tarea")


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///tasks.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        db.create_all()

    @app.get("/")
    def index():
        return redirect(url_for("tasks" if current_user.is_authenticated else "login"))

    @app.route("/registro", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("tasks"))
        form = RegistrationForm()
        if form.validate_on_submit():
            user = User(username=form.username.data.strip())
            user.set_password(form.password.data)
            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                form.username.errors.append("Ese nombre de usuario ya está en uso.")
            else:
                login_user(user)
                flash("Tu cuenta está lista. Vamos con esas tareas.", "success")
                return redirect(url_for("tasks"))
        return render_template("auth.html", form=form, page_title="Crear cuenta", mode="register")

    @app.route("/iniciar-sesion", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("tasks"))
        form = LoginForm()
        if form.validate_on_submit():
            username = form.username.data.strip()
            user = db.session.scalar(select(User).where(User.username == username))
            if user and user.check_password(form.password.data):
                login_user(user)
                flash("Sesión iniciada.", "success")
                return redirect(url_for("tasks"))
            flash("Usuario o contraseña incorrectos.", "error")
        return render_template("auth.html", form=form, page_title="Iniciar sesión", mode="login")

    @app.post("/cerrar-sesion")
    @login_required
    def logout():
        logout_user()
        flash("Has cerrado la sesión.", "info")
        return redirect(url_for("login"))

    @app.get("/tareas")
    @login_required
    def tasks():
        task_list = db.session.scalars(
            select(Task).where(Task.user_id == current_user.id).order_by(Task.created_at.desc())
        ).all()
        form = TaskForm()
        total = len(task_list)
        completed = sum(task.completed for task in task_list)
        return render_template(
            "tasks.html", tasks=task_list, form=form, total=total, completed=completed
        )

    @app.route("/tareas/nueva", methods=["GET", "POST"])
    @login_required
    def create_task():
        form = TaskForm()
        if form.validate_on_submit():
            task = Task(
                title=form.title.data.strip(),
                description=(form.description.data or "").strip(),
                user_id=current_user.id,
            )
            db.session.add(task)
            db.session.commit()
            flash("Tarea añadida.", "success")
            return redirect(url_for("tasks"))
        return render_template("task_form.html", form=form, heading="Nueva tarea")

    @app.route("/tareas/<int:task_id>/editar", methods=["GET", "POST"])
    @login_required
    def edit_task(task_id):
        task = db.session.scalar(
            select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
        )
        if task is None:
            abort(404)
        form = TaskForm(obj=task)
        if form.validate_on_submit():
            task.title = form.title.data.strip()
            task.description = (form.description.data or "").strip()
            task.completed = form.completed.data
            db.session.commit()
            flash("Cambios guardados.", "success")
            return redirect(url_for("tasks"))
        return render_template("task_form.html", form=form, heading="Editar tarea")

    @app.post("/tareas/<int:task_id>/completar")
    @login_required
    def toggle_task(task_id):
        task = db.session.scalar(
            select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
        )
        if task is None:
            abort(404)
        task.completed = not task.completed
        db.session.commit()
        return redirect(url_for("tasks"))

    @app.post("/tareas/<int:task_id>/eliminar")
    @login_required
    def delete_task(task_id):
        task = db.session.scalar(
            select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
        )
        if task is None:
            abort(404)
        db.session.delete(task)
        db.session.commit()
        flash("Tarea eliminada.", "info")
        return redirect(url_for("tasks"))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")