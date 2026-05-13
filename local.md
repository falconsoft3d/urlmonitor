# Ejecutar URLMonitor en local

## Requisitos

- Python 3.10 o superior
- pip

---

## 1. Clonar / ubicarse en el proyecto

```bash
cd /ruta/al/proyecto/urlmonitor
```

## 2. Crear y activar el entorno virtual

```bash
python3 -m venv venv
source venv/bin/activate   # macOS / Linux
# venv\Scripts\activate    # Windows
```

## 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

## 4. Aplicar migraciones

```bash
python manage.py makemigrations monitor
python manage.py migrate
```

## 5. Crear superusuario (opcional, para acceder al admin)

```bash
python manage.py createsuperuser
```

## 6. Iniciar el servidor de desarrollo

```bash
python manage.py runserver
```

La aplicación estará disponible en: **http://127.0.0.1:8000**

---

## Rutas principales

| Ruta                    | Descripción                        |
|-------------------------|------------------------------------|
| `/`                     | Home pública                       |
| `/accounts/register/`   | Registro de usuario                |
| `/accounts/login/`      | Inicio de sesión                   |
| `/accounts/logout/`     | Cerrar sesión (POST)               |
| `/dashboard/`           | Dashboard (requiere login)         |
| `/urls/`                | Lista de URLs registradas          |
| `/urls/agregar/`        | Agregar nueva URL                  |
| `/urls/<id>/editar/`    | Editar URL                         |
| `/urls/<id>/eliminar/`  | Eliminar URL                       |
| `/urls/<id>/verificar/` | Verificar estado de una URL        |
| `/urls/verificar-todas/`| Verificar todas las URLs           |
| `/logs/`                | Historial de verificaciones        |
| `/urls/<id>/detalle/`   | Detalle + métricas de una URL      |
| `/public/<token>/`      | Página pública de estado (sin login) |
| `/config/verificacion/` | Configuración del scheduler        |
| `/config/telegram/`     | Configuración de alertas Telegram  |
| `/admin/`               | Panel de administración de Django  |

---

## Notas

- La base de datos es SQLite (`db.sqlite3`) y se genera automáticamente al migrar.
- Tailwind CSS se carga desde CDN, no requiere instalación adicional.
- El `SECRET_KEY` en `settings.py` es solo para desarrollo; usa una variable de entorno en producción.
