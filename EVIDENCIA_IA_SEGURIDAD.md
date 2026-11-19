# Evidencia de revisión y refactorización asistida por IA

## Alcance y autoría

El sistema MVC de clínica, la integración inicial con OpenFDA y la persistencia
SQLite ya existían antes de esta revisión. El docente autorizó usar ese trabajo
como base. La asistencia de IA se utilizó para revisar y mejorar el proyecto,
no para atribuirse la autoría del sistema completo.

Herramienta: Copilot SDK integrado en VS Code.

## Prompts y respuestas de esta iteración

| Prompt del usuario | Respuesta / trabajo realizado |
|---|---|
| "me puedes hacerlo", junto con la guía y la rúbrica en imágenes | Se revisó la arquitectura existente (MVC, farmacia, API, modelos y DAO) y se priorizaron las brechas de seguridad e integración sin reemplazar el proyecto previo. |
| "me ayudas ejecutarlo bien" | Se ejecutó la aplicación desde la raíz con `python main.py`; se aclaró que las vistas no deben ejecutarse como archivos independientes. |
| "me sale esto" (capturas con `ModuleNotFoundError`) | Se identificó que el botón de ejecución estaba lanzando el archivo dentro de `views` o `tests`; se indicó el comando de entrada correcto y `unittest discover`. |
| "como puedo saber no esta malo" | Se ejecutaron las pruebas y se explicó el significado de `OK` y del conteo de pruebas aprobadas. |
| "si pero comple con todo" | Se amplió el manejo de estados HTTP y validación de JSON, se agregaron pruebas enfocadas y se completó esta evidencia de hallazgos, decisiones y componentes. |

El historial completo de prompts y respuestas permanece en la conversación de
Copilot en VS Code; esta tabla resume las solicitudes relevantes y su resultado
sin presentar el sistema anterior como generado en esta iteración.

## Revisión: hallazgos, cambios y componentes

| Hallazgo / riesgo | Decisión y justificación | Componentes modificados |
|---|---|---|
| SHA-256 directo no incluye salt y permite probar contraseñas rápidamente. | Derivar nuevas claves con PBKDF2-HMAC-SHA256, 200.000 iteraciones y salt aleatorio. Mantener verificación de hashes históricos para no bloquear cuentas existentes y migrarlos después de un ingreso válido. | `models/usuario.py`, `models/usuario_dao.py`, `controllers/auth_controller.py` |
| Parámetros PBKDF2 procedentes de la BD podían solicitar demasiadas iteraciones. | Aceptar solo hashes PBKDF2 con salt/longitud correctos e iteraciones entre 100.000 y 1.000.000. | `models/usuario.py` |
| Respuestas HTTP y JSON externas podían ser incompletas o tener una forma inesperada. | Distinguir 400, 401, 403, 404, 408, 429, 5xx y otros 4xx; comprobar tipos antes de extraer datos y limitar la lectura a cinco resultados. | `services/medicamento_service.py` |
| El API key de OpenFDA se enviaba como Bearer, formato no adecuado para su parámetro documentado. | Enviar `api_key` como parámetro de consulta, conservar `requests`, timeout y verificación TLS. Si no se configura clave, la consulta pública continúa sin ella. | `services/medicamento_service.py`, `config/settings.py` |
| Los errores técnicos de red podían propagarse al usuario. | Mostrar mensajes seguros y activar catálogo local solo para contingencias definidas; no convertir errores de autorización o límite en resultados ficticios. | `services/medicamento_service.py`, `controllers/farmacia_controller.py` |
| No había pruebas directas de estados HTTP, extracción de datos ni JSON inválido. | Probar esas rutas con respuestas simuladas para que sean repetibles y no dependan de Internet. | `tests/test_seguridad.py` |
| La documentación histórica describía el hash SHA-256 inicial. | Añadir una advertencia visible indicando que PBKDF2 es la implementación vigente. | `README_Login.md` |

Las consultas SQLite siguen parametrizadas (`?`); no se reemplazó ese patrón
porque ya protegía contra interpolación de valores en SQL.

## Decisiones consideradas

- **Se conservó la arquitectura MVC y SQLite:** ya cumplen el diseño del
  proyecto y no era necesario introducir otra base de datos o framework.
- **Se conservó `requests`:** está instalado y es una librería oficial/común
  para HTTP en Python; no se añadió dependencia.
- **Se conservó el catálogo de contingencia:** permite continuar si la red o la
  API no están disponibles; los resultados locales se identifican como modo
  contingencia, no como respuesta de OpenFDA.
- **No se implementaron reintentos automáticos:** reintentar límites 429 o
  errores de servidor puede aumentar carga y ocultar la causa; se informa el
  estado y el usuario decide cuándo volver a intentar.
- **No se exponen excepciones ni cuerpo de error de la API:** podrían contener
  información técnica. El detalle se reemplaza por mensajes seguros.
- **No se cambió la receta ni se genera una recomendación médica automática:**
  la respuesta de la API identifica productos/etiquetas, no sustituye el
  criterio profesional para indicar fármacos o dosis.

## Archivos resultantes

- `services/medicamento_service.py`: solicitud HTTP, estados, JSON, extracción,
  validación y contingencia.
- `models/usuario.py`: hashes PBKDF2, validación de formato y compatibilidad.
- `models/usuario_dao.py` y `controllers/auth_controller.py`: migración de
  hashes antiguos e informe de error si no se pudo persistir.
- `views/auth_view.py`: elimina la exposición de la contraseña predeterminada
  en el banner de inicio.
- `tests/test_seguridad.py`: pruebas de credenciales, entrada, HTTP, parsing y
  contingencia.
- `README_Login.md`: advertencia sobre la implementación vigente.
- `README.md`: comandos correctos para iniciar y probar el proyecto desde la raíz.

## Validación ejecutada

Comando, desde la raíz del proyecto:

```powershell
python -m unittest discover -s tests -v
```

Resultado final: 13 pruebas aprobadas. La sintaxis de todos los archivos Python
se validó con `ast.parse`; Bandit analizó 2.008 líneas sin identificar
problemas; también se inició sesión y se cerró la aplicación desde la consola
con código de salida 0. La consulta real a OpenFDA respondió HTTP 200 y entregó
cinco resultados para `aspirin`.

Las pruebas HTTP usan mocks y no requieren una API real; la conectividad real
se comprueba desde la opción de diagnóstico del módulo Farmacia.
