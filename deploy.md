# Deploy URLMonitor en producción — urlmonitor.xyz

Guía completa desde un Ubuntu Server limpio hasta ver los logs en producción con HTTPS.

---

## Requisitos previos

- VPS con **Ubuntu 22.04 LTS** (mínimo 1 vCPU / 1 GB RAM / 20 GB disco)
- Dominio **urlmonitor.xyz** apuntando a la IP del servidor (registro A en tu DNS)
- Acceso SSH como `root` o usuario con `sudo`
- El código del proyecto disponible en un repositorio Git

---

## 1. Actualizar Ubuntu y preparar el servidor

```bash
# Conectarse al servidor
ssh root@<IP_DEL_SERVIDOR>

# Actualizar paquetes
apt update && apt upgrade -y

# Instalar utilidades básicas
apt install -y git curl ufw fail2ban unattended-upgrades

# Habilitar actualizaciones automáticas de seguridad
dpkg-reconfigure --priority=low unattended-upgrades
```

---

## 2. Configurar el firewall (UFW)

```bash
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
ufw status
```

---

## 3. Instalar Docker y Docker Compose

```bash
# Dependencias
apt install -y ca-certificates gnupg lsb-release

# Repositorio oficial de Docker
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Verificar instalación
docker --version
docker compose version

# Iniciar y habilitar Docker en el arranque
systemctl enable --now docker
```

---

## 4. Crear usuario de despliegue (recomendado)

```bash
adduser deploy
usermod -aG docker deploy
# Copiar clave SSH si la usas
rsync --archive --chown=deploy:deploy ~/.ssh /home/deploy/
su - deploy
```

---

## 5. Clonar el repositorio

```bash
# Como root: dar permisos al usuario deploy sobre /opt
chown deploy:deploy /opt

# Cambiar al usuario deploy y clonar
su - deploy
cd /opt
git clone https://github.com/falconsoft3d/urlmonitor.git
cd urlmonitor
```

> Si el repo es privado, usa un token de acceso personal o configura una deploy key.

---

## 6. Configurar variables de entorno

```bash
# Copiar la plantilla
cp .env.example .env

# Editar con tus valores reales
nano .env
```

Ejemplo de `.env` en producción:

```env
SECRET_KEY=pon-aqui-una-clave-secreta-muy-larga-y-aleatoria
DEBUG=False
ALLOWED_HOSTS=urlmonitor.xyz www.urlmonitor.xyz
CSRF_TRUSTED_ORIGINS=https://urlmonitor.xyz https://www.urlmonitor.xyz
TIME_ZONE=Europe/Madrid

# PostgreSQL
DB_NAME=urlmonitor
DB_USER=urlmonitor
DB_PASSWORD=una-password-segura
DB_HOST=db
DB_PORT=5432
```

> Genera una clave segura con:
> ```bash
> python3 -c "import secrets; print(secrets.token_urlsafe(60))"
> ```

---

## 7. Obtener certificado SSL (Let's Encrypt)

El proceso usa dos pasos: primero levantamos nginx solo con HTTP para que
Certbot pueda validar el dominio, luego activamos HTTPS.

### 7a. Activar configuración HTTP temporal

```bash
# Asegúrate de que solo init.conf está activo (sin HTTPS aún)
ls nginx/conf.d/
# Debe mostrar: init.conf  urlmonitor.xyz.conf

# Renombra el archivo HTTPS para que nginx no lo cargue todavía
mv nginx/conf.d/urlmonitor.xyz.conf nginx/conf.d/urlmonitor.xyz.conf.disabled
```

### 7b. Levantar solo nginx (sin web ni certbot)

```bash
docker compose up -d nginx
```

Verifica que responde en HTTP:
```bash
curl -I http://urlmonitor.xyz/.well-known/acme-challenge/test
# Debe devolver 404 (carpeta vacía) — eso significa que nginx responde
```

### 7c. Emitir el certificado

```bash
docker compose run --rm certbot certonly \
  --webroot \
  --webroot-path /var/www/certbot \
  --email admin@urlmonitor.xyz \
  --agree-tos \
  --no-eff-email \
  -d urlmonitor.xyz \
  -d www.urlmonitor.xyz
```

Si todo va bien verás:
```
Successfully received certificate.
Certificate is saved at: /etc/letsencrypt/live/urlmonitor.xyz/fullchain.pem
```

### 7d. Descargar parámetros DH de Let's Encrypt

```bash
docker compose run --rm certbot \
  sh -c "curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf \
    > /etc/letsencrypt/options-ssl-nginx.conf && \
    openssl dhparam -out /etc/letsencrypt/ssl-dhparams.pem 2048"
```

### 7e. Activar configuración HTTPS

```bash
# Elimina init.conf y activa el archivo HTTPS
rm nginx/conf.d/init.conf
mv nginx/conf.d/urlmonitor.xyz.conf.disabled nginx/conf.d/urlmonitor.xyz.conf
```

---

## 8. Construir la imagen y levantar todos los servicios

```bash
# Construir la imagen de Django
docker compose build

# Levantar todo en background
docker compose up -d

# Verificar que los contenedores están corriendo
docker compose ps
```

Deberías ver 3 servicios `Up`:
```
NAME                   STATUS
urlmonitor_web         Up
urlmonitor_nginx       Up
urlmonitor_certbot     Up
```

---

## 9. Crear superusuario de Django

```bash
docker compose exec web python manage.py createsuperuser
```

---

## 10. Verificar que todo funciona

```bash
# HTTPS con certificado válido
curl -I https://urlmonitor.xyz/

# Debe devolver HTTP/2 200 y header: Strict-Transport-Security
```

Abre en el navegador: **https://urlmonitor.xyz**

---

## 11. Ver logs en producción

### Logs en tiempo real (todos los servicios)
```bash
docker compose logs -f
```

### Solo el servidor Django / Gunicorn
```bash
docker compose logs -f web
```

### Solo nginx (accesos y errores)
```bash
docker compose logs -f nginx
```

### Ver las últimas N líneas
```bash
docker compose logs --tail=100 web
```

### Ver logs de un contenedor específico (nombre del contenedor)
```bash
docker logs urlmonitor_web --follow
docker logs urlmonitor_nginx --follow
```

---

## 12. Actualizar la aplicación (deploys futuros)

```bash
cd /opt/urlmonitor

# Bajar los últimos cambios
git pull origin main

# Reconstruir la imagen
docker compose build web

# Reiniciar solo el servicio web (sin downtime en nginx)
docker compose up -d --no-deps web

# Verificar que arrancó bien
docker compose logs --tail=30 web
```

---

## 13. Renovación automática del certificado

El servicio `certbot` en docker-compose.yml ya intenta renovar cada 12 horas automáticamente. Para forzar la renovación manualmente:

```bash
docker compose run --rm certbot renew --webroot -w /var/www/certbot

# Luego recargar nginx para que tome el nuevo certificado
docker compose exec nginx nginx -s reload
```

---

## 14. Backup de la base de datos (PostgreSQL)

```bash
# Dump SQL dentro del contenedor de Postgres
docker compose exec db pg_dump -U urlmonitor urlmonitor \
  > backup-$(date +%F).sql

# Restaurar desde un backup
docker compose exec -T db psql -U urlmonitor urlmonitor \
  < backup-2026-05-13.sql
```

---

## Resumen de comandos útiles

| Tarea | Comando |
|---|---|
| Ver estado de servicios | `docker compose ps` |
| Ver logs en vivo | `docker compose logs -f` |
| Logs solo Django | `docker compose logs -f web` |
| Reiniciar app | `docker compose restart web` |
| Abrir shell en container | `docker compose exec web bash` |
| Ejecutar manage.py | `docker compose exec web python manage.py <cmd>` |
| Parar todo | `docker compose down` |
| Parar y borrar volúmenes | `docker compose down -v` ⚠️ borra datos |
| Reconstruir imagen | `docker compose build web` |
| Actualizar y reiniciar | `git pull && docker compose build web && docker compose up -d --no-deps web` |

---

## Estructura de archivos de deploy

```
urlmonitor/
├── Dockerfile
├── entrypoint.sh
├── docker-compose.yml
├── .env                    ← creado a partir de .env.example (no en git)
├── .env.example
├── .dockerignore
└── nginx/
    ├── conf.d/
    │   ├── init.conf                    ← solo durante la obtención del cert
    │   └── urlmonitor.xyz.conf          ← configuración HTTPS final
    └── certbot/
        ├── conf/                        ← volumen: certificados Let's Encrypt
        └── www/                         ← volumen: validación ACME
```
