import secrets

import pytest
from app import Task, User, create_app, db
from sqlalchemy import select


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


def test_flujo_completo_de_cuenta_y_tareas(client, app):
    sufijo = secrets.token_hex(4)
    username = f"usuario_{sufijo}"
    otro_username = f"otro_{sufijo}"
    password = f"Clave-{sufijo}-segura"
    titulo_inicial = f"Tarea ficticia {sufijo}"
    titulo_editado = f"Tarea actualizada {sufijo}"
    descripcion = f"Descripción de prueba {sufijo}"

    respuesta = client.get("/")
    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].endswith("/iniciar-sesion")

    respuesta = client.get("/tareas")
    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].startswith("/iniciar-sesion")

    respuesta = client.post(
        "/registro",
        data={"username": username, "password": password},
        follow_redirects=True,
    )
    assert respuesta.status_code == 200
    assert b"Lo que tienes" in respuesta.data
    with app.app_context():
        usuario = db.session.scalar(select(User).where(User.username == username))
        assert usuario is not None
        assert usuario.check_password(password)

    respuesta = client.post("/cerrar-sesion")
    assert respuesta.status_code == 302
    respuesta = client.post(
        "/iniciar-sesion",
        data={"username": username, "password": f"incorrecta-{sufijo}"},
        follow_redirects=True,
    )
    assert respuesta.status_code == 200
    assert "Usuario o contraseña incorrectos.".encode() in respuesta.data

    respuesta = client.post(
        "/iniciar-sesion",
        data={"username": username, "password": password},
        follow_redirects=True,
    )
    assert respuesta.status_code == 200
    assert b"Lo que tienes" in respuesta.data

    respuesta = client.post(
        "/tareas/nueva",
        data={"title": titulo_inicial, "description": descripcion},
    )
    assert respuesta.status_code == 302
    with app.app_context():
        tarea = db.session.scalar(select(Task).where(Task.title == titulo_inicial))
        assert tarea is not None
        tarea_id = tarea.id
        assert tarea.description == descripcion
        assert tarea.completed is False
        owner_id = tarea.user_id

    respuesta = client.get("/tareas")
    assert respuesta.status_code == 200
    assert titulo_inicial.encode() in respuesta.data
    assert b"1 tarea" in respuesta.data
    assert b"0 completadas" in respuesta.data

    respuesta = client.post(
        f"/tareas/{tarea_id}/editar",
        data={
            "title": titulo_editado,
            "description": f"Editada {sufijo}",
            "completed": "y",
        },
        follow_redirects=True,
    )
    assert respuesta.status_code == 200
    assert titulo_editado.encode() in respuesta.data
    with app.app_context():
        tarea = db.session.get(Task, tarea_id)
        assert tarea.title == titulo_editado
        assert tarea.description == f"Editada {sufijo}"
        assert tarea.completed is True
        assert tarea.user_id == owner_id

    respuesta = client.get("/tareas")
    assert b"1 completada" in respuesta.data

    respuesta = client.post(f"/tareas/{tarea_id}/completar")
    assert respuesta.status_code == 302
    with app.app_context():
        tarea = db.session.get(Task, tarea_id)
        assert tarea.completed is False

    respuesta = client.post("/cerrar-sesion")
    assert respuesta.status_code == 302
    respuesta = client.post(
        "/registro",
        data={"username": otro_username, "password": password},
        follow_redirects=True,
    )
    assert respuesta.status_code == 200
    respuesta = client.get("/tareas")
    assert otro_username.encode() in respuesta.data
    assert titulo_editado.encode() not in respuesta.data
    assert client.get(f"/tareas/{tarea_id}/editar").status_code == 404
    assert client.post(f"/tareas/{tarea_id}/completar").status_code == 404
    assert client.post(f"/tareas/{tarea_id}/eliminar").status_code == 404
    with app.app_context():
        tarea = db.session.get(Task, tarea_id)
        assert tarea is not None
        assert tarea.title == titulo_editado
        assert tarea.completed is False

    respuesta = client.post("/cerrar-sesion")
    assert respuesta.status_code == 302
    respuesta = client.post(
        "/iniciar-sesion",
        data={"username": username, "password": password},
        follow_redirects=True,
    )
    assert respuesta.status_code == 200

    respuesta = client.post(f"/tareas/{tarea_id}/eliminar")
    assert respuesta.status_code == 302
    with app.app_context():
        assert db.session.get(Task, tarea_id) is None

    respuesta = client.get("/tareas")
    assert respuesta.status_code == 200
    assert titulo_editado.encode() not in respuesta.data
    assert b"0 tareas" in respuesta.data