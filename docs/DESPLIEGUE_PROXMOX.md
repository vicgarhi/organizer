# En orden en Proxmox: LXC + Docker

Esta guía instala **un servidor personal** dentro de un LXC. El ordenador y el móvil abren la misma dirección y usan los mismos datos. Incluye aplicación, proxy Caddy, volúmenes persistentes, arranque automático y herramientas de mantenimiento. No depende de conectores Microsoft.

## 1. Crear el LXC (en Proxmox)

En la interfaz de Proxmox, descarga una plantilla **Debian 12 o Debian 13** y crea un contenedor:

| Ajuste | Recomendación inicial |
| --- | --- |
| Tipo | LXC sin privilegios / Unprivileged |
| CPU | 2 núcleos |
| RAM | 2 GB (4 GB si guardarás muchos adjuntos o harás restores grandes) |
| Swap | 512 MB |
| Disco raíz | 16–20 GB; ampliar si crecen los adjuntos o las imágenes Docker |
| Red | Bridge de tu LAN, normalmente vmbr0; IP fija o reserva DHCP |
| Features | Nesting y keyctl |
| Arranque | Start at boot; orden de arranque después de red/DNS |

Son recursos de partida, no requisitos máximos. Selecciona tu almacenamiento habitual. Los volúmenes Docker quedan dentro del disco raíz del LXC; no hace falta un bind mount externo ni configurar mapeos de UID a mano.

Apaga el contenedor antes de cambiar Features. En un LXC recién creado, la alternativa por CLI **en el host Proxmox** es:

```sh
# Sustituye 123 por el CTID real. En un LXC existente conserva sus otras features.
pct set 123 -features nesting=1,keyctl=1
pct set 123 -onboot 1
pct start 123
pct enter 123
```

A partir de aquí, los comandos se ejecutan **dentro del LXC**, no en el host. Proxmox suele recomendar una VM para Docker cuando se necesita mayor aislamiento/compatibilidad; esta preparación sigue tu elección de LXC. No requiere un LXC privilegiado ni desactivar AppArmor. La compatibilidad final depende de tu versión de Proxmox, kernel y almacenamiento; aquí se prueba Docker, no tu host Proxmox.

## 2. Llevar el proyecto al contenedor

Se entrega `en-orden-lxc.tar.gz` con código y herramientas, **sin contraseñas, datos ni .env**. Junto a él hay un SHA256. Puedes transferirlo por SCP, la consola/gestor de archivos que ya utilices o, si publicas el código en GitHub, clonarlo allí. El código también está disponible en https://github.com/vicgarhi/organizer. Para clonar dentro del LXC (no para instalar Docker en el host Proxmox):

```sh
apt-get update
apt-get install -y git python3
git clone https://github.com/vicgarhi/organizer.git /opt/en-orden
cd /opt/en-orden
```

El clon Git no contiene los wheels binarios del paquete descargable; el configurador utiliza INSTALL_OFFLINE=false y Docker descarga las dependencias desde PyPI.

Ejemplo, desde tu ordenador:

```sh
scp en-orden-lxc.tar.gz en-orden-lxc.tar.gz.sha256 root@IP_DEL_LXC:/tmp/
```

Si SSH no está habilitado en el LXC, usa `pct push` desde el host Proxmox en lugar de habilitarlo solo para este paso:

```sh
pct push 123 /ruta/en-orden-lxc.tar.gz /tmp/en-orden-lxc.tar.gz
pct push 123 /ruta/en-orden-lxc.tar.gz.sha256 /tmp/en-orden-lxc.tar.gz.sha256
```

**Dentro del LXC:**

```sh
cd /tmp
sha256sum -c en-orden-lxc.tar.gz.sha256
mkdir -p /opt/en-orden
# El paquete tiene una carpeta en-orden; no contiene .env ni volúmenes.
tar -xzf en-orden-lxc.tar.gz -C /opt/en-orden --strip-components=1
cd /opt/en-orden
bash deploy/install-docker-debian.sh
```

El instalador usa el repositorio oficial de Docker, verifica su clave de firma y deja activo Docker al arrancar el LXC. Se niega a instalar sobre el host Proxmox o a borrar automáticamente un Docker previo. Requiere salida a Internet para Debian, Docker Hub y download.docker.com. El paquete entregado incluye las dependencias Python ya descargadas y verificadas para Linux x86_64/Python 3.12; el configurador activa INSTALL_OFFLINE=true al encontrarlas y no necesita PyPI durante la compilación. Un paquete generado sin esos wheels utiliza PyPI (INSTALL_OFFLINE=false). No es una instalación completamente sin Internet: las imágenes base y Docker aún deben estar disponibles. Si la clave oficial cambia, verifica el cambio en Docker antes de actualizar el fingerprint; no omitas la verificación.

Si Docker ya está instalado, comprueba el plugin Compose y Python del LXC:

```sh
docker version
docker compose version
python3 --version
# Solo si falta Python:
apt-get update
apt-get install -y python3
```

## 3. Elegir acceso: LAN o HTTPS

### A. Empezar por HTTP en la LAN

```sh
cd /opt/en-orden
python3 scripts/configure_deploy.py --mode http
./scripts/deploy.sh up
./scripts/deploy.sh status
```

Abre `http://IP_DEL_LXC` desde tu ordenador y móvil conectados a esa red. Se publican 80 y 443, pero en este modo solo hay servicio HTTP en 80. **No reenvíes puertos del router a este modo**: la contraseña y los datos viajarían sin TLS. Úsalo únicamente en tu LAN de confianza o por un túnel privado. En el firewall permite 80 solo desde tu LAN. La primera compilación descarga Python y las dependencias; puede tardar varios minutos.

HTTP funciona para tareas, capturas de texto, adjuntos y contexto. En móvil, grabación de micrófono y Web Push requieren un contexto HTTPS válido; una IP por HTTP no los habilita. Para esos flujos utiliza una de las siguientes opciones.

### B. HTTPS con un dominio y certificado público

Si aún no has creado `.env`:

```sh
python3 scripts/configure_deploy.py --mode https --domain organizador.tu-dominio.es
./scripts/deploy.sh up
```

Configura DNS para apuntar al LXC (IP pública/redirección o DNS local según tu instalación). Para la emisión automática de certificado de este Caddyfile, los puertos 80 y 443 deben ser accesibles para las validaciones ACME; un dominio exclusivamente privado sin esa validación no basta. Si lo expones en Internet, habilita solo 80/443 hacia el LXC, nunca 8000. La aplicación exige contraseña, pero mantén Docker, sistema y app actualizados.

`COOKIE_SECURE=true` se establece automáticamente. Accede por `https://organizador.tu-dominio.es`, no por HTTP ni por su IP. No hay configuración de correo ni envío a otras personas.

Si ya tienes un proxy HTTPS en Proxmox (Nginx Proxy Manager, Caddy, Traefik), puedes mantener el modo HTTP **solo como backend privado** y terminar TLS en tu proxy existente. Cambia `COOKIE_SECURE=true` en `.env`, preserva el Host original y pasa las cabeceras estándar. Restringe el puerto del LXC al proxy. El puerto 8000 de la aplicación no se publica. Si quieres escuchar el Caddy interno en otro puerto: `HTTP_PORT=8080`; tu proxy apuntará a `IP_DEL_LXC:8080`.

### C. HTTPS privado con CA de Caddy (sin abrir Internet)

```sh
python3 scripts/configure_deploy.py --mode internal --domain organizador.home.arpa
./scripts/deploy.sh up
```

En tu DNS local/resolver del router crea `organizador.home.arpa → IP_DEL_LXC`. Extrae **solo el certificado público** de la CA y confía en él en cada dispositivo:

```sh
docker compose cp caddy:/data/caddy/pki/authorities/local/root.crt ./enorden-root.crt
```

No compartas `root.key`. Instala el certificado `root.crt` en el almacén de confianza del equipo/móvil. En iOS, además de instalar el perfil, activa la confianza completa en Ajustes → General → Información → Ajustes de confianza de certificados. Un aviso de certificado ignorado no equivale a HTTPS confiable. Comprueba que el navegador no presenta errores TLS antes de probar voz o notificaciones. La compatibilidad con CA propia puede variar por navegador/dispositivo; un certificado público ya gestionado por tu proxy suele ser más sencillo para móvil.

### Cambiar de modo después

El configurador **no sobrescribe .env**. Edita ese fichero privado:

```text
# HTTP LAN:
APP_ADDRESS=:80
CADDY_CONFIG=deploy/Caddyfile
COOKIE_SECURE=false

# HTTPS público:
APP_ADDRESS=organizador.tu-dominio.es
CADDY_CONFIG=deploy/Caddyfile
COOKIE_SECURE=true

# HTTPS interno:
APP_ADDRESS=organizador.home.arpa
CADDY_CONFIG=deploy/Caddyfile.internal
COOKIE_SECURE=true
```

Guarda solo un bloque de valores y ejecuta `docker compose up -d --force-recreate organizer caddy`. Cambiar HTTP/HTTPS no borra tus datos. Mantén `.env` con permisos 0600 y fuera de Git.

## 4. Primer acceso y datos actuales

Si no estableces `APP_PASSWORD`, el primer arranque genera una contraseña aleatoria privada. **En tu terminal privado del LXC**, consulta:

```sh
cd /opt/en-orden
docker compose exec organizer cat /data/initial-password.txt
```

No pegues esa salida en chats ni logs compartidos. Para elegir tu contraseña y eliminar el fichero inicial:

```sh
# Parar solo la app evita sesiones activas durante el cambio.
docker compose stop organizer
docker compose run --rm --no-deps --entrypoint python organizer scripts/set_password.py
docker compose up -d --wait
```

Usa al menos 12 caracteres. Si has fijado `APP_PASSWORD` en `.env`, cambia esa variable en lugar de usar el script; al recrear la app se aplica el valor de `.env`. No necesitas añadir la contraseña a .env cuando utilizas la generada o el script.

La app nueva contiene los datos reales iniciales de la especificación. Para trasladar datos de la instancia anterior, usa **Ajustes → Exportar copia completa** allí y **Ajustes → Recuperar una copia** en el LXC. También se entrega un ZIP separado `en-orden-datos.zip`, con los datos presentes en este entorno al prepararlo; es privado y no contiene claves ni sesiones. La importación sustituye datos: exporta primero si ya has trabajado en el LXC. El ZIP de la aplicación es distinto de la copia física descrita abajo y se importa desde la interfaz, no con `deploy.sh restore`.

El compromiso de conciliación del 5 de octubre de 2026 se conserva como dato original, aunque ya haya pasado cuando despliegues.

## 5. IA y notificaciones opcionales

La base funciona sin servicios de pago. Para IA, añade `OPENAI_API_KEY` en `.env` o en el gestor de secretos que utilices; `AI_MODEL` es configurable. No subas esa clave al frontend ni a Git. Después:

```sh
docker compose up -d --force-recreate organizer
```

La app consulta `api.openai.com`. La configuración no garantiza acceso, saldo ni autorización corporativa para tratar datos de clientes.

Para Web Push, primero configura HTTPS válido y después genera VAPID:

```sh
docker compose exec organizer python scripts/generate_push.py mailto:tu-correo@example.com
```

Eso escribe `/data/push.env` dentro del volumen privado. La app no carga archivos dotenv automáticamente: traslada en tu terminal privado las tres variables de ese fichero a `.env` (sin pegarlas en logs o chats) y recrea la app. Se puede consultar ese fichero mediante `docker compose exec organizer cat /data/push.env` **solo en tu terminal privado**. Conserva las claves entre actualizaciones. En Ajustes activa cada dispositivo y envía el aviso de prueba. En iPhone/iPad se necesita iOS 16.4+ y abrir la app añadida a pantalla de inicio. El servidor debe seguir activo para enviar avisos; el proveedor aceptarlos no garantiza entrega.

Voz se guarda como audio. Transcripción, OCR, lectura de PDF/Office, correo reenviado y conectores Microsoft siguen pendientes; Docker no añade esas capacidades. En la aplicación aparecen identificadas. Las tarifas actuales de IA no están verificadas. En tu propio Proxmox no hay cuota adicional de alojamiento en este código, pero sí recursos, electricidad, copias y consumo opcional de API.

## 6. Copias y recuperación

Desde `/opt/en-orden`:

```sh
./scripts/deploy.sh backup
```

La copia física se escribe en `backups/enorden-FECHA.tar.gz`, permisos 0600. Detiene brevemente aplicación y proxy para copiar coherentemente SQLite y archivos, luego los vuelve a arrancar. Incluye:

- Base de datos, adjuntos, sesiones y configuración local de acceso.
- `.env`, incluidas claves opcionales si las has guardado allí.
- Almacenamiento de Caddy, incluida su CA privada/certificados.

**Esta copia sí contiene secretos**. Transfiérela cifrada fuera del LXC y prueba su recuperación. No basta con guardar backups en el mismo disco del servicio. Límite de la herramienta de recuperación: 128 MB comprimidos y 2 GB de contenido de volúmenes; para conjuntos mayores usa una copia offline del volumen o backup del LXC.

Para recuperar una copia física, primero instala el paquete y arranca el conjunto vacío en el nuevo LXC; después:

```sh
./scripts/deploy.sh restore /ruta/enorden-FECHA.tar.gz --confirm
```

Valida el formato/rutas antes de cambiar nada, guarda automáticamente una copia del estado actual y restaura datos, acceso, .env y CA. Sustituye los datos existentes. Si falla durante la escritura o el arranque, revisa el error y utiliza la copia previa de `backups/`; no se afirma una restauración atómica de los dos volúmenes. En otro servidor, revisa IP/DNS y puertos de la configuración recuperada antes de abrir el servicio. Las copias físicas son para el proyecto Compose `enorden`, no para nombres personalizados.

Para copia programada como root en el LXC, crea una entrada en `crontab -e`:

```cron
30 3 * * * cd /opt/en-orden && ./scripts/deploy.sh backup >> /var/log/enorden-backup.log 2>&1
```

El horario del cron sigue la zona del sistema del LXC (consulta `timedatectl`), que puede diferir de la zona configurada en la aplicación. Programa transferencia externa, alertas y retención según tu infraestructura. La herramienta no borra backups antiguos. La ejecución interrumpe el servicio; elige un horario apropiado. Proxmox Backup Server/vzdump complementa esto: con los volúmenes en el disco raíz se incluyen en la copia del LXC. Para máxima coherencia del conjunto utiliza un backup con parada o coordínalo con la parada de los servicios; un snapshot tomado durante escrituras no sustituye probar la recuperación. Si mueves el almacenamiento a un mount point, comprueba expresamente que Proxmox lo incluya.

## 7. Actualizaciones y arranque automático

Docker utiliza `restart: unless-stopped`; Proxmox debe tener `Start at boot` activado. Si paras manualmente servicios, vuelve a ejecutarlos cuando los necesites:

```sh
./scripts/deploy.sh up
./scripts/deploy.sh status
./scripts/deploy.sh logs
./scripts/deploy.sh stop
```

Para actualizar, conserva el paquete anterior, instala el nuevo código en `/opt/en-orden` y conserva `.env`, `backups/` y los volúmenes. Los paquetes no incluyen esos archivos, así que extraer una versión nueva no los sobrescribe. Después:

```sh
./scripts/deploy.sh update
```

Primero construye la imagen: si falla la compilación, no detiene el servicio existente. Después hace copia física y recrea los servicios con comprobación de salud. La copia restaura datos/configuración; para volver al código anterior también hay que conservar y desplegar la versión anterior del paquete. No ejecutes `docker compose down -v`: eliminaría los volúmenes. Las actualizaciones de Caddy/Docker/Debian se gestionan aparte; prueba antes y mantén una copia recuperable.

## 8. Verificación y diagnóstico

```sh
docker compose ps
curl --fail http://IP_DEL_LXC/api/health
# En modo HTTPS, usa la URL HTTPS y una CA confiable, sin desactivar TLS.
```

`organizer` debe aparecer healthy. `caddy` running. Entra, captura una nota, revisa/acepta y comprueba el asunto desde el móvil. Reinicia el LXC y verifica que los datos y el acceso se mantienen. Exporta una copia y recupera en un entorno de prueba. Si falta una clave opcional, la app debe indicarlo.

| Síntoma | Revisar |
| --- | --- |
| Docker no arranca dentro del LXC | Nesting/keyctl, versión de Proxmox/kernel, logs de Docker (`journalctl -u docker`) y documentación de compatibilidad. No conviertas el contenedor en privilegiado como primer paso. |
| Error overlayfs/storage driver | Disco/subvolumen y soporte del kernel. Considera disco adecuado, driver soportado o VM; no borres `/var/lib/docker` para probar. |
| No abre la IP | IP del LXC, bridge, firewall, puertos 80/443 y `docker compose ps`. |
| Login entra pero vuelve a pedir contraseña | COOKIE_SECURE=true con acceso HTTP, o Host/Origin alterado por un proxy. |
| Caddy no emite certificado | Dominio/DNS, acceso ACME por 80/443 y logs de caddy. Para dominio privado usa CA interna o tu proxy existente. |
| Permiso denegado en /data | Debe usarse el volumen nombrado creado por Docker. App UID/GID 10001; un bind mount personalizado necesita permisos equivalentes. |
| Docker Hub devuelve toomanyrequests/429 | Límite de descargas anónimas: autentica Docker con `docker login` en tu terminal privado o espera a su restablecimiento. No compartas tokens en chats. |
| Fallo al descargar dependencias | DNS y salida del LXC a Docker Hub/PyPI, proxy si lo utilizas. No desactives TLS ni firmas para resolverlo. |
| Voz/push no disponibles en móvil | HTTPS válido, permisos, compatibilidad e instalación PWA en iOS; claves VAPID y acceso del servidor al proveedor. |

La base Python está fijada por digest y Caddy por versión para reproducibilidad; actualízalos de forma deliberada cuando apliques actualizaciones de seguridad. En otra arquitectura regenera los wheels en un entorno Python 3.12/Linux compatible, o elimina los `.whl` de deploy/wheels y utiliza INSTALL_OFFLINE=false.

Las pruebas realizadas aquí se registran en `docs/VERIFICACION_DESPLIEGUE.md`. No implican acceso a tu Proxmox ni validación de tu DNS, certificado público o teléfono físico.
