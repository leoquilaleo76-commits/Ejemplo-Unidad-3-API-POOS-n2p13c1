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