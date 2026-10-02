# En orden

Organizador privado para un consultor de finanzas y tesorería. Captura sin clasificación obligatoria, revisión, clientes y asuntos, tareas con contexto, seguimientos, recordatorios y exportación para Claude. La especificación completa está en [docs/ESPECIFICACION.md](docs/ESPECIFICACION.md) y las decisiones en [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md).

## Arranque local

Python 3.12+, Linux/macOS. Desde la raíz:

```sh
./scripts/install.sh
./scripts/start.sh
```

El servidor escucha en el puerto 8000, por defecto solo en la máquina local. Para otro puerto usar `PORT=8080`. Los datos se conservan en `.data/` (ignorado por Git); `DATA_DIR` permite un disco persistente externo. No borrar esta carpeta para actualizar. El primer arranque carga únicamente los datos reales de la especificación; no crea ejemplos ficticios. El compromiso de conciliación sigue siendo 2026-10-05, incluso si la fecha ya pasó.

Al primer arranque, si no existe configuración de acceso, se genera una contraseña aleatoria en `.data/initial-password.txt`, con permisos 0600. Consúltala **solo en tu terminal privado**, sin compartirla en chats ni registros. Cambiarla mediante `.venv/bin/python scripts/set_password.py` y reiniciar; se invalidan las sesiones y se elimina el archivo inicial. Alternativa: `APP_PASSWORD` en el gestor de secretos del servidor (al arrancar se aplica su hash). Evita rotar una contraseña si el servidor sigue activo; reinicia inmediatamente tras el cambio. El fichero de contraseña inicial no se regenera al borrar solo ese fichero: conservar `access.json` mantiene el acceso existente.

No se necesita Node ni compilación. La interfaz carga todos sus recursos localmente.

## Uso

- Mi día: disponibilidad en minutos, prioridades explicadas, compromisos y esperas. Revisa la selección antes de reservar las tareas para hoy.
- Captura rápida: texto, archivos y grabación de audio. Se conserva el contenido original. Se puede guardar información sin tareas.
- Revisión: corregir cliente/asunto, texto, acciones y fechas; aceptar o descartar. Doble aceptación de la misma propuesta no duplica acciones. La coincidencia exacta de título/asunto evita duplicados abiertos; la detección semántica no está garantizada.
- Asuntos: resumen editable, acciones, notas, documentos, fuentes e historial. Exporta el contexto en texto para Claude.
- Tarea: edición sencilla, completar/reabrir explícitamente, recuperar última edición, registrar avance mediante frase y llevarlo a revisión. No se completa al pasar el día.
- Seguimientos: datos desconocidos pueden quedar vacíos. No envía reclamaciones a otras personas.
- Recordatorios: una vez, diario, laborables, semanal o mensual; se programa la siguiente repetición cuando lo marcas hecho. Aviso por día, sin hora específica.
- Ajustes: zona horaria, estado de integraciones, copias ZIP completas y recuperación. Exporta antes de recuperar, porque la recuperación sustituye los datos. Máximo 100 MB por copia y 15 MB por adjunto.

## IA real, opcional

Configura `OPENAI_API_KEY` **en el servidor** y, opcionalmente, `AI_MODEL` (por defecto `gpt-4.1-mini`). Reinicia. La API usada es Chat Completions de OpenAI, destino `api.openai.com`. Cada botón de análisis/consulta hace una petición real; errores del proveedor aparecen como tales y la captura sigue guardada. En un entorno con red restringida hay que autorizar ese dominio y su binding de credencial.

Sin clave, las sugerencias son **reglas locales**, identificadas en pantalla. El asistente local enumera datos guardados y fuentes; no simula IA ni genera un borrador ficticio. El resumen puede copiarse a Claude como alternativa. No hay análisis de audio, PDF, imágenes u Office: se almacenan y descargan. El navegador incorpora el texto de .txt/.md/.eml de menos de 1 MB, incluidas sus cabeceras originales. Archivos .eml con MIME complejo no se decodifican semánticamente.

Antes de enviar información de clientes a una API, comprueba tus políticas corporativas. Un análisis solo se solicita mediante acción explícita, no por subir un adjunto. La IA no ejecuta cambios ni envía mensajes. Consulta las limitaciones de las instrucciones contra inyección en arquitectura.

## Notificaciones móviles reales

Implementadas mediante Service Worker + Web Push + VAPID. No dependen de mantener una pestaña abierta. El servidor debe seguir activo, tener acceso a Internet a los proveedores push y servir HTTPS. El scheduler comprueba cada minuto los recordatorios explícitos y las fechas de compromiso/seguimiento de tareas abiertas; envía una notificación por fecha, no por cada minuto. No se notifica una propuesta de planificación. Si no hay suscripciones, no se marca enviado; si hay varios dispositivos, la recepción no es una garantía y no hay reintento por dispositivo una vez algún proveedor acepta.

Genera la identidad en el servidor:

```sh
.venv/bin/python scripts/generate_push.py mailto:tu-correo@example.com
set -a
. .data/push.env
set +a
./scripts/start.sh
```

El generador escribe las claves en un fichero privado sin imprimirlas. Conserva la misma identidad VAPID entre reinicios; rotarla requiere volver a suscribir dispositivos. Puedes trasladar `VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY` y `VAPID_SUBJECT` a tu gestor de secretos. Ajustes → Activar en este dispositivo → Aviso de prueba. El aviso de prueba informa de que el proveedor lo aceptó, no asegura recepción.

Android: navegador compatible, HTTPS y permiso. iPhone/iPad: iOS/iPadOS 16.4+, añadir a pantalla de inicio, abrir desde el icono y conceder permiso por una acción explícita. Se incluyen manifiesto y service worker. No se han verificado dispositivos físicos ni envío real sin claves VAPID configuradas. La grabación de voz también requiere HTTPS (o contexto local seguro) y permiso del micrófono.

Destinos push admitidos por seguridad: FCM (`fcm.googleapis.com`), Mozilla (`updates.push.services.mozilla.com`), Apple (`*.push.apple.com`) y Windows (`*.notify.windows.com`). En red restringida hay que autorizar los dominios utilizados. No se permite un endpoint arbitrario para evitar peticiones desde el servidor a servicios internos.

## Despliegue en Proxmox (LXC + Docker)

La preparación completa está en [docs/DESPLIEGUE_PROXMOX.md](docs/DESPLIEGUE_PROXMOX.md). Incluye LXC Debian sin privilegios, Docker oficial, proxy Caddy, opciones HTTP LAN/HTTPS, acceso, migración, backups físicos, restauración y actualizaciones.

Dentro del LXC, con el proyecto en `/opt/en-orden`:

```sh
bash deploy/install-docker-debian.sh
python3 scripts/configure_deploy.py --mode http
./scripts/deploy.sh up
```

Abre la IP del LXC por HTTP solo en tu red de confianza. Para móvil con voz/Web Push utiliza HTTPS: dominio público, tu proxy existente o CA interna confiable. Nunca publiques 8000. `compose.yaml` gestiona aplicación, Caddy y volúmenes persistentes; `.env` queda privado. El configurador no sobrescribe archivos existentes.

Las herramientas `./scripts/deploy.sh backup`, `restore COPIA --confirm` y `update` conservan datos; la copia física incluye secretos y debe guardarse cifrada fuera del LXC. No usar `docker compose down -v`. La interfaz también exporta ZIP sin contraseñas para migrar datos entre servidores.

Un solo servidor y una base SQLite: ordenador y móvil usan los mismos datos, con refresco para ver cambios de otra sesión. No hay sincronización en tiempo real. El despliegue en tu Proxmox, DNS y servicios opcionales se realizan siguiendo la guía; no se afirma que estén ya configurados allí.

## Costes y viabilidad

SQLite, FastAPI y este código no cobran licencia. Web Push/VAPID no exige un servicio de pago de nuestra parte; sí servidor permanente, HTTPS y compatibilidad del dispositivo. El alojamiento, dominio, backup externo e IA pueden costar dinero. Las claves, DNS, servidor y disco persistente están pendientes del despliegue elegido.

**Presupuesto propuesto, no tarifas verificadas:** reservar 5–10 €/mes para servidor pequeño y almacenamiento, 1–3 € para copias/dominio prorrateado, y un tope externo de 5–7 € para IA. Eso cabe aproximadamente en 20 € solo con uso moderado y un proveedor adecuado; impuestos, almacenamiento y consumo pueden superarlo. Los límites/budgets del proveedor pueden ser avisos, no un corte duro. La aplicación no impone todavía un límite de gasto.

Se intentó consultar las páginas oficiales de [Hetzner Cloud](https://www.hetzner.com/cloud/) y [OpenAI API](https://openai.com/api/pricing/) el 2 de octubre de 2026; la red del entorno devolvió 403 en ambas. No se afirman precios actuales ni planes gratuitos. Verifica esas tarifas antes de contratar y empieza sin IA si necesitas coste predecible. El despliegue no exige usar esos proveedores.

## Verificación

```sh
.venv/bin/python -m unittest discover -s tests -v
# Opcional: instalar Playwright en el entorno de pruebas y disponer de Chromium.
python3 tests/browser_check.py
# Usar CHROMIUM_PATH=/ruta/al/chromium si no está en /usr/bin/chromium.
```

Las pruebas usan carpetas temporales y no modifican datos personales. Las pruebas de API cubren acceso, CSRF, capturas, revisión, duplicados, recuperación de cambios, conservación de fechas, disponibilidad, dependencias, adjuntos, exportación/restauración y estados de servicios. La prueba de navegador recorre captura → corrección → aceptación → contexto → avance → consulta basada en fuentes, dos sesiones/dispositivos y vistas de escritorio/móvil, con imágenes en `test-results/` (ignoradas por Git). No sustituye una prueba de notificaciones en un teléfono físico.

## Pendiente de siguientes iteraciones

Recepción de correos reenviados, transcripción de voz, OCR y lectura semántica de documentos, citas precisas por página, conectores de Microsoft, edición natural de tareas existentes más allá de guardar avances, extracción/revisión de acuerdos con tipología separada y planificación por bloques horarios. Esta base es funcional y persistente, pero esas funciones no se presentan como implementadas.
