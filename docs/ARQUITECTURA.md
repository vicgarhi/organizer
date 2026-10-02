# Decisiones y fases

Aplicación monousuario, sin conectores corporativos. Servidor FastAPI (Python 3.12), SQLite con claves foráneas y transacciones, archivos en disco persistente. Interfaz HTML/CSS/JavaScript sin compilación ni dependencias de CDN. Español de España, zona Europe/Madrid configurable. No hay datos personales en localStorage ni caché del service worker. Un mismo servidor HTTPS permite usar los mismos datos en ordenador y móvil.

1. Modelo: cliente → asunto → acciones, capturas originales y adjuntos. Compromiso, trabajo, seguimiento, estimación, responsable y dependencia son campos separados y nullable.
2. Recorrido: captura inmediata → propuesta local conservadora → análisis IA opcional → corrección → aceptación transaccional → contexto/historial → avance como nueva captura. Una actualización no completa tareas. Edición manual explícita, estado y resumen auditados. Las revisiones se deshacen si no destruyen trabajo posterior; ediciones de tareas recuperan el estado anterior.
3. Diseño: portada editorial, tres acciones propuestas como máximo, un contexto destacado y compromisos/esperas al lado; navegación inferior en móvil y detalles en diálogo. Sin métricas ficticias.
4. Integraciones: API de OpenAI solo desde el servidor; Web Push con VAPID y worker periódico en un único proceso; grabación de voz como adjunto; importación textual de .txt/.md/.eml. No recepción automática de correo ni conectores Microsoft.
5. Verificación: pruebas de API con datos temporales, recorrido Chromium con dos sesiones y siete vistas en móvil/escritorio, exportación/restauración y persistencia al reiniciar.

## Planificador

La selección es heurística y revisable: compromisos cercanos, trabajo con estimación en asuntos con compromiso, fechas de trabajo elegidas, seguimientos vencidos y demás pendientes. Las dependencias abiertas y esperas quedan fuera de acciones ejecutables. No propone más de tres acciones, evita superar los minutos conocidos disponibles y no reserva ninguna si hay cero minutos. Las tareas con fecha de trabajo futura permanecen fuera. Las duraciones desconocidas no se estiman: se explica que el total es incompleto. Aceptar reserva fechas de trabajo de la selección para hoy; no cambia compromisos ni crea citas. Lo no seleccionado conserva su estado y su fecha previa. No es un calendario con optimización de franjas horarias.

## Seguridad y límites

Contraseña PBKDF2-SHA256 con sal aleatoria, sesiones opacas persistidas mediante hash, cookies HttpOnly/SameSite con Secure en despliegue, límite de intentos de acceso, comprobación de origen y cabecera para escrituras, CSP y escape de contenido en la interfaz. No se registra el contenido de claves ni credenciales. No se envían mensajes a terceros. Documentos y correos se delimitan como datos en las instrucciones del modelo. Una IA puede equivocarse o sufrir inyección de instrucciones: no se confía en su resultado; se validan referencias/campos y toda propuesta se revisa antes de aplicar. No se promete inmunidad.

Los datos/adjuntos no están cifrados en reposo por la aplicación. Usar disco cifrado del proveedor, acceso restringido y copias cifradas. No exponer Uvicorn sin HTTPS. El despliegue es de un solo proceso; múltiples workers duplicarían el scheduler de avisos. No es SaaS multiusuario ni requiere permisos de equipo. Las copias no contienen contraseñas, claves ni suscripciones push. Los adjuntos sin interpretación siguen disponibles para descargar, no se afirma que se hayan leído.
