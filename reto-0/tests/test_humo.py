from app import app


def test_pagina_principal_responde():
    cliente = app.test_client()
    respuesta = cliente.get("/", follow_redirects=True)
    assert respuesta.status_code == 200