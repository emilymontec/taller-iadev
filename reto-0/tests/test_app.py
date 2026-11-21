import pytest
from sqlalchemy import select

from app import Task, create_app, db


@pytest.fixture
def app():
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "WTF_CSRF_ENABLED": False,
        }
    )
    with application.app_context():
        db.drop_all()
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def register(client, username):
    return client.post(
        "/registro",
        data={"username": username, "password": "password-segura"},
        follow_redirects=True,
    )


def test_account_registration_and_login(client):
    response = register(client, "ana")
    assert response.status_code == 200
    assert b"Lo que tienes" in response.data

    client.post("/cerrar-sesion")
    response = client.post(
        "/iniciar-sesion",
        data={"username": "ana", "password": "password-segura"},
        follow_redirects=True,
    )
    assert b"Lo que tienes" in response.data


def test_user_can_create_edit_complete_and_delete_task(client, app):
    register(client, "ana")
    client.post("/tareas/nueva", data={"title": "Leer", "description": "Capítulo uno"})
    with app.app_context():
        task = db.session.scalar(select(Task).where(Task.title == "Leer"))
        task_id = task.id

    response = client.post(
        f"/tareas/{task_id}/editar",
        data={"title": "Leer hoy", "description": "Antes de dormir", "completed": "y"},
        follow_redirects=True,
    )
    assert b"Leer hoy" in response.data
    with app.app_context():
        task = db.session.get(Task, task_id)
        assert task.title == "Leer hoy"
        assert task.description == "Antes de dormir"
        assert task.completed is True

    client.post(f"/tareas/{task_id}/completar")
    with app.app_context():
        assert db.session.get(Task, task_id).completed is False

    client.post(f"/tareas/{task_id}/eliminar")
    with app.app_context():
        assert db.session.get(Task, task_id) is None


def test_user_cannot_read_or_mutate_another_users_task(client, app):
    register(client, "ana")
    client.post("/tareas/nueva", data={"title": "Privada de Ana"})
    with app.app_context():
        task = db.session.scalar(select(Task).where(Task.title == "Privada de Ana"))
        task_id = task.id

    client.post("/cerrar-sesion")
    register(client, "luis")
    assert b"Privada de Ana" not in client.get("/tareas").data
    assert client.get(f"/tareas/{task_id}/editar").status_code == 404
    assert client.post(f"/tareas/{task_id}/completar").status_code == 404
    assert client.post(f"/tareas/{task_id}/eliminar").status_code == 404

    with app.app_context():
        task = db.session.get(Task, task_id)
        assert task.title == "Privada de Ana"
        assert task.completed is False