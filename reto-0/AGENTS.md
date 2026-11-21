# AGENTS.md

## Proyecto
Aplicación web "Día a día" para gestionar tareas personales con cuentas de usuario.
Permite registrarse, iniciar sesión y crear, editar, completar y eliminar tareas propias.

## Stack
- Framework: Flask 3.1 con Flask-Login, Flask-WTF/WTForms y Jinja2.
- Base de datos: SQLite vía Flask-SQLAlchemy.
- Librerías: python-dotenv para variables de entorno; pytest para pruebas.

## Comandos
- Instalar: `python -m venv .venv`, activar `.\.venv\Scripts\Activate.ps1` y `pip install -r requirements.txt`.
- Ejecutar: copiar `.env.example` a `.env` y `flask --app app run --debug`.
- Pruebas: `python -m pytest -v`.
- Estilo: `ruff check .`.

## Estructura
- `app.py`: fábrica de la app, modelos `User`/`Task`, formularios y rutas.
- `requirements.txt`: dependencias del proyecto.
- `.env.example`: plantilla de variables de entorno (sin secretos reales).
- `.env`: valores locales reales; no se versiona.
- `.gitignore`: excluye `.venv`, cachés, `instance/`, `*.db` y `.env`.
- `README`: instrucciones de instalación y ejecución.
- `templates/`: vistas Jinja2 de la interfaz.
  - `base.html`: plantilla base, cabecera y mensajes flash.
  - `auth.html`: formulario de registro e inicio de sesión.
  - `tasks.html`: listado de tareas y resumen de progreso.
  - `task_form.html`: formulario para crear y editar tareas.
- `static/`: recursos estáticos.
  - `styles.css`: estilos de la interfaz.
- `tests/`: pruebas automatizadas.
  - `test_app.py`: pruebas de autenticación, CRUD y aislamiento entre usuarios.
- `instance/`: base SQLite generada automáticamente; no se versiona.
- `.venv/`, `__pycache__/`, `.pytest_cache/`: entornos y cachés generados; no editar.

## Qué no hacer
- No modificar las pruebas para que pasen.
- No escribir claves en el código.
- No instalar dependencias sin explicar para qué.
- No hacer commit ni push.

## Lecciones aprendidas
"La lógica de negocio se mantiene separada de las rutas en el módulo servicios.py."
