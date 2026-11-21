import os
import secrets
from datetime import UTC, datetime

from dotenv import load_dotenv
from flask import Flask
from flask_login import LoginManager, UserMixin
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
        if find_user_by_username(field.data.strip()):
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


def find_user_by_username(username):
    return db.session.scalar(select(User).where(User.username == username))


def create_user(username, password):
    user = User(username=username.strip())
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return None
    return user


def authenticate_user(username, password):
    user = find_user_by_username(username.strip())
    if user and user.check_password(password):
        return user
    return None


def list_tasks(user_id):
    return db.session.scalars(
        select(Task).where(Task.user_id == user_id).order_by(Task.created_at.desc())
    ).all()


def count_tasks(tasks):
    return len(tasks), sum(task.completed for task in tasks)


def create_task(title, description, user_id):
    task = Task(
        title=title.strip(),
        description=(description or "").strip(),
        user_id=user_id,
    )
    db.session.add(task)
    db.session.commit()
    return task


def get_owned_task(task_id, user_id):
    return db.session.scalar(
        select(Task).where(Task.id == task_id, Task.user_id == user_id)
    )


def update_task(task, title, description, completed):
    task.title = title.strip()
    task.description = (description or "").strip()
    task.completed = completed
    db.session.commit()


def toggle_task(task):
    task.completed = not task.completed
    db.session.commit()


def delete_task(task):
    db.session.delete(task)
    db.session.commit()


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

    from app import register_routes

    register_routes(app)

    with app.app_context():
        db.create_all()

    return app
