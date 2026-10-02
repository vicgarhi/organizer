# Verificación del despliegue

Realizada el 2 de octubre de 2026 en este entorno de desarrollo, con Docker 28.4.0 y Compose v2.40.3, Linux x86_64. Se utilizó un stack desechable con volúmenes independientes de los datos de la instancia original.

## Resultados

| Comprobación | Resultado |
| --- | --- |
| `docker compose config --quiet` | Correcto |
| Generación HTTP/HTTPS público/HTTPS interno | Correcta; permisos .env 0600; no sobrescribe configuración existente |
| Bash y Python de herramientas | Sintaxis correcta |
| Pruebas automatizadas del servidor y despliegue | 17 superadas |
| Imagen de aplicación | Compilada con Python fijado por digest y dependencias offline verificadas con SHA256 |
| Dependencias dentro de la imagen | `pip check`: sin incompatibilidades |
| Arranque | UID 10001, filesystem de imagen de solo lectura, volumen persistente y healthcheck healthy |
| Configuraciones Caddy | HTTP y TLS interno validados con Caddy oficial 2.10.2 |
| HTTP por proxy | Health, login privado, captura, aceptación y adjunto con descarga correcta |
| Copia física y recuperación | Se recuperaron captura aceptada, tarea y adjunto; se conservó el compromiso original |
| Reinicio de aplicación | Datos y sesión persistidos |
| Actualización | Imagen compilada, copia previa generada, servicios recreados y saludables |
| HTTPS interno | CA y hostname verificados; login con cookie Secure/HttpOnly y consulta autenticada |
| Paquete portable | Sin .env, credenciales, .data ni backups; checksum SHA256 adjunto |

La prueba real encontró permisos insuficientes de los archivos de aplicación copiados a la imagen; se corrigió usando propietario UID/GID 10001 en COPY. También se verificó la protección de las rutas del formato de copia contra traversal, enlaces y destinos no permitidos.

## Condiciones de la prueba

El contenedor de compilación no pudo resolver PyPI, aun con red host/proxy. Se descargaron las dependencias por el entorno anfitrión mediante pip con verificación TLS, se prepararon wheels y sus SHA256, y se compiló con INSTALL_OFFLINE=true. El paquete portable incluye esos wheels para Linux x86_64/Python 3.12. No se han desactivado TLS, firmas ni comprobaciones de integridad.

Docker Hub impidió descargar la imagen `caddy:2.10.2-alpine` por límite de descargas anónimas; los mirrors probados no estaban permitidos por la red. Para completar las pruebas se descargó Caddy 2.10.2 desde la publicación oficial en GitHub, se verificó su **SHA512** frente al fichero oficial de checksums y se utilizó ese ejecutable en una imagen temporal de validación basada en la imagen local. Esa imagen temporal no se entrega ni es la imagen por defecto: Compose mantiene la imagen oficial de Caddy para instalar desde tu red. Por tanto se ha probado el ejecutable/configuración del proxy y el recorrido Docker, pero no la descarga o arranque de la imagen Alpine exacta desde este entorno.

El primer request HTTPS se hizo mientras Caddy todavía estaba emitiendo el certificado interno. Tras verificar la emisión en sus logs, se repitió y pasó con CA confiable y validación de hostname, sin opciones de TLS inseguro. El estado running de Caddy no prueba por sí solo que un certificado público ya se haya emitido.

## No verificado aquí

- Creación/arranque de un LXC en tu host Proxmox, su kernel, filesystem, firewall o features.
- DNS de tu dominio y emisión pública ACME. La opción HTTPS pública está configurada, pero requiere DNS/red reales.
- Confianza de CA y voz/push en tu teléfono físico.
- IA y envíos Web Push reales: faltan sus claves opcionales.
- Instalación de Docker por apt dentro de un Debian nuevo: el script se ha revisado y comprobado sintácticamente, no ejecutado sobre este host.

Estas condiciones no se presentan como operaciones realizadas en tu infraestructura. La guía de despliegue incluye los pasos para verificarlas allí.
