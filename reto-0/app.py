import os

from flask import abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required, login_user, logout_user
from servicios import (
    LoginForm,
    RegistrationForm,
    Task,
    TaskForm,
    User,
    authenticate_user,
    count_tasks,
    create_app,
    create_user,
    db,
    get_owned_task,
    list_tasks,
    update_task,
)
from servicios import (
    create_task as create_task_service,
)
from servicios import (
    delete_task as delete_task_service,
)
from servicios import (
    toggle_task as toggle_task_service,
)

__all__ = ["Task", "User", "app", "create_app", "db", "register_routes"]


def register_routes(app):
    @app.get("/")
    def index():
        return redirect(url_for("tasks" if current_user.is_authenticated else "login"))

    @app.route("/registro", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("tasks"))
        form = RegistrationForm()
        if form.validate_on_submit():
            user = create_user(form.username.data, form.password.data)
            if user is None:
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
            user = authenticate_user(form.username.data, form.password.data)
            if user:
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
        task_list = list_tasks(current_user.id)
        total, completed = count_tasks(task_list)
        form = TaskForm()
        return render_template(
            "tasks.html", tasks=task_list, form=form, total=total, completed=completed
        )

    @app.route("/tareas/nueva", methods=["GET", "POST"])
    @login_required
    def create_task():
        form = TaskForm()
        if form.validate_on_submit():
            create_task_service(form.title.data, form.description.data, current_user.id)
            flash("Tarea añadida.", "success")
            return redirect(url_for("tasks"))
        return render_template("task_form.html", form=form, heading="Nueva tarea")

    @app.route("/tareas/<int:task_id>/editar", methods=["GET", "POST"])
    @login_required
    def edit_task(task_id):
        task = get_owned_task(task_id, current_user.id)
        if task is None:
            abort(404)
        form = TaskForm(obj=task)
        if form.validate_on_submit():
            update_task(task, form.title.data, form.description.data, form.completed.data)
            flash("Cambios guardados.", "success")
            return redirect(url_for("tasks"))
        return render_template("task_form.html", form=form, heading="Editar tarea")

    @app.post("/tareas/<int:task_id>/completar")
    @login_required
    def toggle_task(task_id):
        task = get_owned_task(task_id, current_user.id)
        if task is None:
            abort(404)
        toggle_task_service(task)
        return redirect(url_for("tasks"))

    @app.post("/tareas/<int:task_id>/eliminar")
    @login_required
    def delete_task(task_id):
        task = get_owned_task(task_id, current_user.id)
        if task is None:
            abort(404)
        delete_task_service(task)
        flash("Tarea eliminada.", "info")
        return redirect(url_for("tasks"))


app = create_app()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
