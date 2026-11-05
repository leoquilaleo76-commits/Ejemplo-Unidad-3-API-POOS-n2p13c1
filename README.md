# GUÍA PRÁCTICA DE INTEGRACIÓN: DE MVC LOCAL A SERVICIOS EXTERNOS (APIs)
## Sistema de Gestión Clínica – Módulo de Farmacia y Recetas Médicas

> **Objetivo de la guía:**  
> Tomar como base tu proyecto de la Clínica (que ya gestiona `Pacientes` y `Departamentos` en consola con base de datos SQLite) y aprender a **conectar la aplicación a una API pública externa**, gestionar credenciales de forma segura con variables de entorno, controlar caídas de red y **persistir los datos obtenidos de internet directamente en la base de datos local**.

---

## 1. ¿Qué vamos a construir y por qué?

En un hospital o clínica real, los médicos no escriben los nombres de los medicamentos a mano sin control (evitando errores de digitación o recetar fármacos inexistentes). 

En esta integración:
1. El médico ingresará el nombre de un medicamento o principio activo.
2. Nuestro sistema **consultará en tiempo real una API internacional oficial de fármacos (OpenFDA)**.
3. El sistema recibirá los datos en formato **JSON**, los convertirá en objetos de Python y los mostrará en pantalla.
4. El médico seleccionará el fármaco, definirá la dosis y el sistema **guardará la receta de forma permanente en la base de datos local SQLite**, asociada al RUT del paciente.

---

## 2. Mapa Arquitectónico: ¿Dónde encaja la API en el patrón MVC?

Para no romper el orden ni mezclar responsabilidades:
* **La Vista (`views/`):** Solo se encarga de mostrar datos (`print`) y pedir información (`input`). **Jamás** hace llamadas HTTP ni toca la base de datos.
* **El Modelo y DAO (`models/`):** Define cómo es un `Medicamento` y cómo se guarda una `Receta` en SQLite con consultas parametrizadas.
* **La nueva capa de Servicio (`services/`):** Es la especialista en comunicarse con el mundo exterior. Hace las peticiones HTTP con `requests`, controla los tiempos de espera (*timeouts*) y gestiona los posibles errores de conexión.
* **El Controlador (`controllers/`):** Es el director de orquesta que coordina a la Vista, al Servicio de API y al DAO.

```text
       [ USUARIO EN CONSOLA ]
                 │
                 ▼
          ┌─────────────┐
          │    VISTA    │ (views/farmacia_view.py)
          └──────┬──────┘
                 │
                 ▼
       ┌───────────────────┐
       │    CONTROLADOR    │ (controllers/farmacia_controller.py)
       └────┬─────────┬────┘
            │         │
            │         └──────────────────────────┐
            ▼                                    ▼
     ┌─────────────┐                      ┌─────────────┐
     │   SERVICE   │                      │     DAO     │ (models/receta_dao.py)
     │    (API)    │                      │  (SQLite)   │
     └──────┬──────┘                      └──────┬──────┘
            │                                    │
            ▼                                    ▼
    [ INTERNET / API ]                     [ clinica.db ]
   (Servicio Externo)                     (Base de Datos)
```

---

## 3. Paso a Paso para la Integración

---

### PASO 1: Instalar dependencias necesarias

Para comunicarnos con servicios web y gestionar configuraciones seguras, utilizaremos librerías estándar en la industria.

1. En la raíz de tu proyecto, crea un archivo llamado `requirements.txt`:
```text
requests>=2.31.0
python-dotenv>=1.0.0
bandit>=1.7.5
```

2. Abre tu terminal en la carpeta del proyecto y ejecuta:
```bash
pip install -r requirements.txt
```

* **`requests`**: Librería para realizar peticiones HTTP (GET, POST, etc.) de forma limpia.
* **`python-dotenv`**: Permite leer configuraciones desde un archivo oculto `.env` sin exponer datos sensibles.
* **`bandit`**: Herramienta de auditoría estática para comprobar que nuestro código no tenga fallos de seguridad.

---

### PASO 2: Gestión segura de configuraciones (.env y settings.py)

> [!WARNING]
> **Regla de oro de seguridad:** NUNCA escribas URLs sensibles, tokens o claves de acceso directamente dentro de archivos `.py`. Si subes tu código a GitHub, cualquiera podría robar tus credenciales.

1. Crea en la raíz del proyecto un archivo llamado `.env` (este archivo guardará tus valores locales):
```env
API_BASE_URL=https://api.fda.gov/drug/label.json
API_KEY=clave_de_acceso_laboratorio_2026
REQUEST_TIMEOUT=5
ENABLE_OFFLINE_FALLBACK=True
```

2. Crea un archivo `.env.example` (plantilla pública que sirve de guía para otros desarrolladores sin exponer secretos reales):
```env
API_BASE_URL=https://api.fda.gov/drug/label.json
API_KEY=tu_api_key_aqui
REQUEST_TIMEOUT=5
ENABLE_OFFLINE_FALLBACK=True
```

3. Abre tu archivo `.gitignore` y asegúrate de incluir `.env`:
```text
__pycache__/
*.py[cod]
.DS_Store
clinica.db
.env
```

4. Dentro de la carpeta `config/`, crea el archivo `config/settings.py` para leer estas variables de forma centralizada:
```python
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)
except ImportError:
    pass

class Settings:
    """
    Centraliza las variables de configuración del sistema.
    Evita exponer credenciales hardcodeadas en el código fuente.
    """
    API_BASE_URL: str = os.getenv("API_BASE_URL", "https://api.fda.gov/drug/label.json")
    API_KEY: str = os.getenv("API_KEY", "")
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "5"))
    ENABLE_OFFLINE_FALLBACK: bool = os.getenv("ENABLE_OFFLINE_FALLBACK", "True").lower() in ("true", "1", "yes")
```

---

### PASO 3: Extender la Base de Datos SQLite

Necesitamos una nueva tabla en SQLite para guardar las recetas médicas emitidas y asociarlas a los pacientes existentes.

Abre `config/database.py` y dentro del método `init_db()` añade la creación de la tabla `receta`:

```python
# Tabla Receta (Persistencia local de fármacos consultados por API)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS receta (
        id_receta INTEGER PRIMARY KEY AUTOINCREMENT,
        rut_paciente TEXT NOT NULL,
        nombre_medicamento TEXT NOT NULL,
        principio_activo TEXT,
        dosis TEXT NOT NULL,
        indicaciones TEXT,
        fecha_emision TEXT NOT NULL,
        FOREIGN KEY(rut_paciente) REFERENCES paciente(rut) ON DELETE CASCADE
    )
""")
```

> [!NOTE]
> Nota cómo `rut_paciente` actúa como **Clave Foránea (FOREIGN KEY)** enlazada a la tabla `paciente`. Esto asegura integridad relacional.

---

### PASO 4: Crear los Modelos de Dominio (`Medicamento` y `Receta`)

1. Crea el archivo `models/medicamento.py`:
Representa el fármaco tal como lo entrega el servicio externo, aplicando encapsulamiento con `@property` y `@setter`.

```python
class Medicamento:
    """
    Modelo de Dominio para representar un medicamento obtenido desde la API externa.
    """
    def __init__(
        self,
        nombre_comercial: str,
        nombre_generico: str = "",
        principio_activo: str = "",
        proposito: str = "",
        fabricante: str = ""
    ):
        self.nombre_comercial = nombre_comercial
        self.nombre_generico = nombre_generico
        self.principio_activo = principio_activo
        self.proposito = proposito
        self.fabricante = fabricante

    @property
    def nombre_comercial(self) -> str:
        return self._nombre_comercial

    @nombre_comercial.setter
    def nombre_comercial(self, valor: str) -> None:
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError("El nombre comercial del medicamento no puede estar vacío.")
        self._nombre_comercial = valor.strip().title()

    @property
    def nombre_generico(self) -> str:
        return self._nombre_generico

    @nombre_generico.setter
    def nombre_generico(self, valor: str) -> None:
        self._nombre_generico = (valor or "No especificado").strip().title()

    @property
    def principio_activo(self) -> str:
        return self._principio_activo

    @principio_activo.setter
    def principio_activo(self, valor: str) -> None:
        self._principio_activo = (valor or "No especificado").strip().title()

    @property
    def proposito(self) -> str:
        return self._proposito

    @proposito.setter
    def proposito(self, valor: str) -> None:
        self._proposito = (valor or "Uso general").strip()

    @property
    def fabricante(self) -> str:
        return self._fabricante

    @fabricante.setter
    def fabricante(self, valor: str) -> None:
        self._fabricante = (valor or "Laboratorio no informado").strip()

    def __str__(self) -> str:
        return (
            f"Medicamento: {self.nombre_comercial} ({self.nombre_generico}) | "
            f"Activo: {self.principio_activo} | Fabricante: {self.fabricante}"
        )
```

2. Crea el archivo `models/receta.py`:
Representa la orden médica emitida a un paciente en particular.

```python
from datetime import datetime

class Receta:
    """
    Modelo de Dominio para una Receta Médica emitida.
    """
    def __init__(
        self,
        rut_paciente: str,
        nombre_medicamento: str,
        dosis: str,
        indicaciones: str = "",
        principio_activo: str = "",
        fecha_emision: str | None = None,
        id_receta: int | None = None
    ):
        self.id_receta = id_receta
        self.rut_paciente = rut_paciente
        self.nombre_medicamento = nombre_medicamento
        self.principio_activo = principio_activo
        self.dosis = dosis
        self.indicaciones = indicaciones
        self.fecha_emision = fecha_emision or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @property
    def rut_paciente(self) -> str:
        return self._rut_paciente

    @rut_paciente.setter
    def rut_paciente(self, valor: str) -> None:
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError("El RUT del paciente no puede estar vacío.")
        self._rut_paciente = valor.strip().upper()

    @property
    def nombre_medicamento(self) -> str:
        return self._nombre_medicamento

    @nombre_medicamento.setter
    def nombre_medicamento(self, valor: str) -> None:
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError("El nombre del medicamento no puede estar vacío.")
        self._nombre_medicamento = valor.strip().title()

    @property
    def dosis(self) -> str:
        return self._dosis

    @dosis.setter
    def dosis(self, valor: str) -> None:
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError("La dosis debe ser especificada (ej. '500 mg cada 8 horas').")
        self._dosis = valor.strip()

    def __str__(self) -> str:
        return (
            f"Receta #{self.id_receta or 'Nueva'} | Paciente: {self.rut_paciente} | "
            f"Fármaco: {self.nombre_medicamento} ({self.principio_activo}) | "
            f"Dosis: {self.dosis} | Fecha: {self.fecha_emision}"
        )
```

---

### PASO 5: Crear el DAO para la Persistencia Local (`models/receta_dao.py`)

Crea `models/receta_dao.py` para interactuar con SQLite mediante consultas parametrizadas (`?`):

```python
import sqlite3
from typing import List, Optional
from config.database import Database
from models.receta import Receta

class RecetaDAO:
    """
    Data Access Object para la persistencia local de recetas médicas en SQLite.
    """
    def __init__(self):
        self.db = Database()

    def insertar(self, receta: Receta) -> Optional[int]:
        """Guarda una nueva receta y devuelve el ID generado."""
        sql = """
            INSERT INTO receta (rut_paciente, nombre_medicamento, principio_activo, dosis, indicaciones, fecha_emision)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                sql,
                (
                    receta.rut_paciente,
                    receta.nombre_medicamento,
                    receta.principio_activo,
                    receta.dosis,
                    receta.indicaciones,
                    receta.fecha_emision
                )
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error al registrar receta en BD: {e}")
            return None
        finally:
            conn.close()

    def obtener_por_paciente(self, rut: str) -> List[Receta]:
        """Obtiene el historial de recetas de un paciente específico."""
        sql = """
            SELECT id_receta, rut_paciente, nombre_medicamento, principio_activo, dosis, indicaciones, fecha_emision
            FROM receta
            WHERE rut_paciente = ?
            ORDER BY id_receta DESC
        """
        conn = self.db.get_connection()
        recetas = []
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (rut.strip().upper(),))
            for fila in cursor.fetchall():
                recetas.append(Receta(
                    id_receta=fila["id_receta"],
                    rut_paciente=fila["rut_paciente"],
                    nombre_medicamento=fila["nombre_medicamento"],
                    principio_activo=fila["principio_activo"],
                    dosis=fila["dosis"],
                    indicaciones=fila["indicaciones"],
                    fecha_emision=fila["fecha_emision"]
                ))
        except sqlite3.Error as e:
            print(f"Error al consultar recetas: {e}")
        finally:
            conn.close()
        return recetas

    def listar_todas(self) -> List[Receta]:
        """Lista todas las recetas emitidas en la clínica."""
        sql = """
            SELECT id_receta, rut_paciente, nombre_medicamento, principio_activo, dosis, indicaciones, fecha_emision
            FROM receta
            ORDER BY id_receta DESC
        """
        conn = self.db.get_connection()
        recetas = []
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            for fila in cursor.fetchall():
                recetas.append(Receta(
                    id_receta=fila["id_receta"],
                    rut_paciente=fila["rut_paciente"],
                    nombre_medicamento=fila["nombre_medicamento"],
                    principio_activo=fila["principio_activo"],
                    dosis=fila["dosis"],
                    indicaciones=fila["indicaciones"],
                    fecha_emision=fila["fecha_emision"]
                ))
        except sqlite3.Error as e:
            print(f"Error al listar recetas: {e}")
        finally:
            conn.close()
        return recetas
```

---

### PASO 6: Construir el Servicio de Consumo de API (`services/medicamento_service.py`)

Crea la carpeta `services/` y dentro de ella crea dos archivos:
1. `services/__init__.py` (vacío).
2. `services/medicamento_service.py` con la lógica de conexión externa:

```python
import re
from typing import List, Tuple

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None
    REQUESTS_AVAILABLE = False

from config.settings import Settings
from models.medicamento import Medicamento

class MedicamentoService:
    """
    Servicio encargado de consumir la API externa de medicamentos.
    Implementa buenas prácticas de seguridad, sanitización y tolerancia a fallos.
    """

    # Catálogo de respaldo local por si se corta internet en el laboratorio
    CATALOGO_CONTINGENCIA = [
        Medicamento("Paracetamol", "Acetaminofén", "Paracetamol 500mg", "Analgésico y antipirético", "Laboratorio Chile"),
        Medicamento("Ibuprofeno", "Ibuprofeno", "Ibuprofeno 400mg", "Antiinflamatorio no esteroideo", "Laboratorio Andrómaco"),
        Medicamento("Amoxicilina", "Amoxicilina", "Amoxicilina 500mg", "Antibiótico bactericida", "Laboratorio Saval"),
        Medicamento("Loratadina", "Loratadina", "Loratadina 10mg", "Antihistamínico para alergias", "Laboratorio Mintlab"),
        Medicamento("Omeprazol", "Omeprazol", "Omeprazol 20mg", "Inhibidor de bomba de protones", "Laboratorio Pasteur")
    ]

    @staticmethod
    def sanitizar_termino(termino: str) -> str:
        """Valida que la entrada del usuario no contenga caracteres maliciosos."""
        if not termino or not isinstance(termino, str):
            raise ValueError("El término de búsqueda debe ser un texto válido.")
        
        limpio = termino.strip()
        if not re.match(r"^[a-zA-Z0-9\sáéíóúÁÉÍÓÚñÑ]+$", limpio):
            raise ValueError("El término contiene caracteres no permitidos.")
        
        if len(limpio) < 2:
            raise ValueError("Ingrese al menos 2 caracteres para la búsqueda.")
            
        return limpio

    @classmethod
    def buscar_medicamentos(cls, termino: str) -> Tuple[List[Medicamento], str]:
        """Consulta la API externa con el término solicitado."""
        termino_seguro = cls.sanitizar_termino(termino)

        if not REQUESTS_AVAILABLE:
            return cls._manejar_contingencia(
                termino_seguro, 
                "Librería 'requests' no instalada en el entorno."
            )

        headers = {
            "Accept": "application/json",
            "User-Agent": "ClinicaSeguraApp/1.0"
        }
        
        # Inyección segura de token si existe
        if Settings.API_KEY:
            headers["Authorization"] = f"Bearer {Settings.API_KEY}"

        params = {
            "search": f'openfda.brand_name:"{termino_seguro}" openfda.generic_name:"{termino_seguro}"',
            "limit": 5
        }

        try:
            # Siempre se define un timeout explícito para que el software no se congele
            response = requests.get(
                Settings.API_BASE_URL,
                headers=headers,
                params=params,
                timeout=Settings.REQUEST_TIMEOUT
            )

            # Manejo de códigos HTTP comunes
            if response.status_code == 404:
                return ([], f"No se encontraron medicamentos coincidentes con '{termino_seguro}'.")
            elif response.status_code == 401:
                return ([], "Error 401: Acceso no autorizado a la API externa.")
            elif response.status_code == 429:
                return ([], "Error 429: Límite de consultas a la API excedido.")
            
            response.raise_for_status()

            # Deserialización del JSON
            data = response.json()
            resultados = data.get("results", [])
            medicamentos: List[Medicamento] = []

            for item in resultados:
                openfda = item.get("openfda", {})
                marcas = openfda.get("brand_name", [])
                genericos = openfda.get("generic_name", [])
                fabricantes = openfda.get("manufacturer_name", [])
                sustancias = openfda.get("substance_name", [])
                proposito_raw = item.get("purpose", ["Uso terapéutico"])

                nombre_comercial = marcas[0] if marcas else (genericos[0] if genericos else termino_seguro)
                nombre_generico = genericos[0] if genericos else "No especificado"
                principio = sustancias[0] if sustancias else nombre_generico
                fabricante = fabricantes[0] if fabricantes else "No informado"
                proposito = proposito_raw[0] if isinstance(proposito_raw, list) and proposito_raw else str(proposito_raw)

                medicamentos.append(Medicamento(
                    nombre_comercial=nombre_comercial,
                    nombre_generico=nombre_generico,
                    principio_activo=principio,
                    proposito=proposito[:100],
                    fabricante=fabricante
                ))

            return (medicamentos, f"Se encontraron {len(medicamentos)} medicamentos en el servicio externo.")

        except requests.exceptions.Timeout:
            return cls._manejar_contingencia(
                termino_seguro, 
                f"El servicio tardó más de {Settings.REQUEST_TIMEOUT}s en responder (Timeout)."
            )
        except requests.exceptions.ConnectionError:
            return cls._manejar_contingencia(
                termino_seguro, 
                "No hay conexión a internet o el servidor externo está caído."
            )
        except requests.exceptions.RequestException as e:
            return cls._manejar_contingencia(termino_seguro, f"Falla en la petición: {str(e)}")

    @classmethod
    def _manejar_contingencia(cls, termino: str, causa_error: str) -> Tuple[List[Medicamento], str]:
        """Si la conexión falla, permite seguir trabajando con datos locales de contingencia."""
        if not Settings.ENABLE_OFFLINE_FALLBACK:
            return ([], f"{causa_error} (El modo offline está deshabilitado).")

        termino_norm = termino.lower()
        coincidentes = [
            m for m in cls.CATALOGO_CONTINGENCIA
            if termino_norm in m.nombre_comercial.lower() or termino_norm in m.principio_activo.lower()
        ]

        msg = (
            f"[MODO CONTINGENCIA] {causa_error}\n"
            f"Se cargó el catálogo local de emergencia ({len(coincidentes)} resultados)."
        )
        return (coincidentes, msg)

    @classmethod
    def probar_conectividad(cls) -> Tuple[bool, str]:
        """Verifica si la API externa está accesible."""
        if not REQUESTS_AVAILABLE:
            return (False, "Librería 'requests' no instalada. Ejecute 'pip install requests'.")

        try:
            resp = requests.get(
                Settings.API_BASE_URL,
                params={"limit": 1},
                timeout=Settings.REQUEST_TIMEOUT
            )
            if resp.status_code in (200, 404):
                return (True, f"Conexión exitosa con {Settings.API_BASE_URL} (Código HTTP: {resp.status_code})")
            return (False, f"El servidor respondió con código HTTP: {resp.status_code}")
        except requests.exceptions.Timeout:
            return (False, "Timeout al contactar el servicio.")
        except requests.exceptions.ConnectionError:
            return (False, "Sin conexión de red hacia el servidor.")
        except Exception as e:
            return (False, f"Error de red: {str(e)}")
```

---

### PASO 7: Crear la Vista del Módulo (`views/farmacia_view.py`)

Crea `views/farmacia_view.py`:

```python
from typing import List, Optional
from views.utils import leer_numero, confirmar
from models.medicamento import Medicamento
from models.receta import Receta

class FarmaciaView:
    """
    Vista de consola para el módulo de Farmacia.
    """
    @staticmethod
    def mostrar_menu() -> int:
        print("\n" + "="*50)
        print("         MÓDULO DE FARMACIA Y RECETAS")
        print("="*50)
        print("1.- Consultar Medicamento en API Externa")
        print("2.- Prescribir Medicamento a Paciente (Guardar en BD)")
        print("3.- Ver Recetas de un Paciente por RUT")
        print("4.- Listar Todas las Recetas Emitidas")
        print("5.- Diagnosticar Conexión con API Externa")
        print("0.- Volver al Menú Principal")
        print("="*50)
        return leer_numero("Seleccione una opción: ")

    @staticmethod
    def pedir_termino_busqueda() -> str:
        print("\n--- BÚSQUEDA EN SERVICIO EXTERNO ---")
        return input("Ingrese nombre o principio activo (ej. 'aspirin', 'ibuprofen'): ").strip()

    @staticmethod
    def mostrar_medicamentos(medicamentos: List[Medicamento]) -> None:
        if not medicamentos:
            print("\n[INFO] No hay medicamentos para mostrar.")
            return

        print(f"\n--- RESULTADOS OBTENIDOS ({len(medicamentos)}) ---")
        for i, med in enumerate(medicamentos, start=1):
            print(f"[{i}] {med.nombre_comercial}")
            print(f"    - Nombre Genérico : {med.nombre_generico}")
            print(f"    - Principio Activo: {med.principio_activo}")
            print(f"    - Fabricante      : {med.fabricante}")
            print(f"    - Indicación/Uso  : {med.proposito}")
            print("-" * 45)

    @staticmethod
    def seleccionar_medicamento(medicamentos: List[Medicamento]) -> Optional[Medicamento]:
        if not medicamentos:
            return None
        while True:
            opc = leer_numero("\nSeleccione el número del medicamento a prescribir (0 para cancelar): ")
            if opc == 0:
                return None
            if 1 <= opc <= len(medicamentos):
                return medicamentos[opc - 1]
            print(f"Por favor, ingrese un número entre 1 y {len(medicamentos)}.")

    @staticmethod
    def pedir_datos_receta(medicamento: Medicamento) -> Optional[dict]:
        print(f"\n--- PRESCRIPCIÓN DE: {medicamento.nombre_comercial} ---")
        rut = input("Ingrese RUT del paciente receptor: ").strip().upper()
        if not rut:
            print("Error: El RUT no puede quedar vacío.")
            return None

        dosis = input("Ingrese la dosis y posología (ej. '1 comprimido cada 8 hrs por 5 días'): ").strip()
        if not dosis:
            print("Error: La dosis es obligatoria.")
            return None

        indicaciones = input("Indicaciones adicionales (opcional): ").strip()

        if not confirmar("¿Confirma la emisión y guardado de esta receta médica?"):
            print("Operación cancelada.")
            return None

        return {
            "rut_paciente": rut,
            "dosis": dosis,
            "indicaciones": indicaciones
        }

    @staticmethod
    def pedir_rut_busqueda() -> str:
        return input("\nIngrese el RUT del paciente a consultar: ").strip().upper()

    @staticmethod
    def mostrar_recetas(recetas: List[Receta]) -> None:
        if not recetas:
            print("\n[INFO] No se registraron recetas médicas para el paciente.")
            return

        print(f"\n--- HISTORIAL DE RECETAS MÉDICAS ({len(recetas)}) ---")
        for r in recetas:
            print(f"• Receta #{r.id_receta} | Fecha: {r.fecha_emision}")
            print(f"  Paciente : {r.rut_paciente}")
            print(f"  Fármaco  : {r.nombre_medicamento} ({r.principio_activo})")
            print(f"  Dosis    : {r.dosis}")
            if r.indicaciones:
                print(f"  Detalle  : {r.indicaciones}")
            print("-" * 40)

    @staticmethod
    def mostrar_mensaje(mensaje: str) -> None:
        print(f"\n[SISTEMA] {mensaje}")

    @staticmethod
    def mostrar_error(error: str) -> None:
        print(f"\n[ERROR] {error}")
```

---

### PASO 8: Crear el Controlador (`controllers/farmacia_controller.py`)

Crea `controllers/farmacia_controller.py`:

```python
from views.farmacia_view import FarmaciaView
from services.medicamento_service import MedicamentoService
from models.receta import Receta
from models.receta_dao import RecetaDAO
from models.paciente_dao import PacienteDAO

class FarmaciaController:
    """
    Controlador que orquesta la vista, el servicio de API y la persistencia en BD.
    """
    def __init__(self):
        self.view = FarmaciaView()
        self.service = MedicamentoService()
        self.receta_dao = RecetaDAO()
        self.paciente_dao = PacienteDAO()

    def ejecutar(self) -> None:
        while True:
            opcion = self.view.mostrar_menu()
            if opcion == 1:
                self.consultar_medicamentos()
            elif opcion == 2:
                self.prescribir_medicamento()
            elif opcion == 3:
                self.consultar_recetas_paciente()
            elif opcion == 4:
                self.listar_todas_recetas()
            elif opcion == 5:
                self.diagnosticar_conexion()
            elif opcion == 0:
                break
            else:
                self.view.mostrar_error("Opción no válida. Intente nuevamente.")

    def consultar_medicamentos(self) -> None:
        termino = self.view.pedir_termino_busqueda()
        if not termino:
            return
        try:
            medicamentos, estado = self.service.buscar_medicamentos(termino)
            self.view.mostrar_mensaje(estado)
            self.view.mostrar_medicamentos(medicamentos)
        except ValueError as e:
            self.view.mostrar_error(str(e))
        except Exception as e:
            self.view.mostrar_error(f"Error inesperado: {str(e)}")

    def prescribir_medicamento(self) -> None:
        termino = self.view.pedir_termino_busqueda()
        if not termino:
            return

        try:
            medicamentos, estado = self.service.buscar_medicamentos(termino)
            self.view.mostrar_mensaje(estado)
            if not medicamentos:
                return

            self.view.mostrar_medicamentos(medicamentos)
            med_seleccionado = self.view.seleccionar_medicamento(medicamentos)
            if not med_seleccionado:
                return

            datos_receta = self.view.pedir_datos_receta(med_seleccionado)
            if not datos_receta:
                return

            rut = datos_receta["rut_paciente"]

            # Regla de Negocio: el paciente debe existir previamente en la BD local
            paciente = self.paciente_dao.obtener_por_rut(rut)
            if not paciente:
                self.view.mostrar_error(
                    f"El paciente con RUT '{rut}' no está registrado en el sistema. "
                    "Debe registrarlo primero en el módulo de Pacientes antes de recetar."
                )
                return

            # Crear la receta con los datos combinados (API + Paciente local)
            nueva_receta = Receta(
                rut_paciente=rut,
                nombre_medicamento=med_seleccionado.nombre_comercial,
                principio_activo=med_seleccionado.principio_activo,
                dosis=datos_receta["dosis"],
                indicaciones=datos_receta["indicaciones"]
            )

            # Persistencia en SQLite
            id_generado = self.receta_dao.insertar(nueva_receta)
            if id_generado:
                nueva_receta.id_receta = id_generado
                self.view.mostrar_mensaje(
                    f"¡Receta #{id_generado} emitida y guardada con éxito en SQLite!\n"
                    f"Paciente: {paciente.nombre} ({paciente.rut}) | Medicamento: {nueva_receta.nombre_medicamento}"
                )
            else:
                self.view.mostrar_error("No se pudo guardar la receta en la base de datos.")

        except ValueError as e:
            self.view.mostrar_error(str(e))
        except Exception as e:
            self.view.mostrar_error(f"Error al emitir receta: {str(e)}")

    def consultar_recetas_paciente(self) -> None:
        rut = self.view.pedir_rut_busqueda()
        if not rut:
            return
        recetas = self.receta_dao.obtener_por_paciente(rut)
        self.view.mostrar_recetas(recetas)

    def listar_todas_recetas(self) -> None:
        recetas = self.receta_dao.listar_todas()
        self.view.mostrar_recetas(recetas)

    def diagnosticar_conexion(self) -> None:
        self.view.mostrar_mensaje("Verificando conectividad con el servicio externo...")
        exito, detalle = self.service.probar_conectividad()
        if exito:
            self.view.mostrar_mensaje(f"[ONLINE] {detalle}")
        else:
            self.view.mostrar_error(f"[OFFLINE] {detalle}")
```

---

### PASO 9: Integrar todo en el Menú Principal

Para que el usuario pueda acceder al nuevo módulo desde la consola:

1. **Modifica `views/main_view.py`:**
```python
from views.utils import leer_numero

class MainView:
    @staticmethod
    def mostrar_menu() -> int:
        print("\n" + "="*50)
        print("     CLÍNICA SANITARIA - MENÚ PRINCIPAL")
        print("="*50)
        print("1.- Gestión de Pacientes")
        print("2.- Gestión de Departamentos")
        print("3.- Farmacia y Recetas Médicas (Consumo de API)")
        print("0.- Salir del Sistema")
        print("="*50)
        return leer_numero("Seleccione una opción: ")

    @staticmethod
    def mostrar_mensaje(mensaje: str) -> None:
        print(f"\n[SISTEMA] {mensaje}")
```

2. **Modifica `controllers/main_controller.py`:**
```python
from views.main_view import MainView
from controllers.paciente_controller import PacienteController
from controllers.departamento_controller import DepartamentoController
from controllers.farmacia_controller import FarmaciaController

class MainController:
    def __init__(self):
        self.view = MainView()
        self.paciente_controller = PacienteController()
        self.departamento_controller = DepartamentoController()
        self.farmacia_controller = FarmaciaController()

    def ejecutar(self) -> None:
        while True:
            opcion = self.view.mostrar_menu()
            if opcion == 1:
                self.paciente_controller.ejecutar()
            elif opcion == 2:
                self.departamento_controller.ejecutar()
            elif opcion == 3:
                self.farmacia_controller.ejecutar()
            elif opcion == 0:
                self.view.mostrar_mensaje("Gracias por usar el sistema de la Clínica. ¡Hasta luego!")
                break
            else:
                self.view.mostrar_mensaje("Opción no válida. Por favor, intente nuevamente.")
```

---

## 4. Cómo Probar el Sistema (Guía de Verificación)

1. **Inicia la aplicación:**
   ```bash
   python main.py
   ```

2. **Paso A: Registrar un paciente**
   * Elige la opción `1.- Gestión de Pacientes` -> `1.- Crear Paciente`.
   * Ingresa un paciente (ejemplo: RUT `11.111.111-1`, Nombre `Ana Lopez`, Edad `28`, Previsión `Fonasa`).

3. **Paso B: Probar la conexión a la API**
   * Vuelve al menú principal y entra a `3.- Farmacia y Recetas Médicas`.
   * Elige `5.- Diagnosticar Conexión con API Externa`.
   * Deberías ver un mensaje `[ONLINE]` confirmando la respuesta del servidor.

4. **Paso C: Consultar y prescribir un fármaco**
   * Elige `2.- Prescribir Medicamento a Paciente`.
   * Ingresa un término de búsqueda (ej. `aspirin` o `ibuprofeno`).
   * Selecciona el número del medicamento mostrado.
   * Ingresa el RUT del paciente creado (`11.111.111-1`), la dosis y confirma.
   * El sistema emitirá la receta y la guardará en la base de datos `clinica.db`.

5. **Paso D: Validar la persistencia**
   * Elige `3.- Ver Recetas de un Paciente por RUT` e introduce el RUT.
   * Verás el historial de recetas emitidas para ese paciente con su fecha y dosis.
   * Puedes cerrar el programa y volver a abrirlo: los datos seguirán guardados gracias a SQLite.

