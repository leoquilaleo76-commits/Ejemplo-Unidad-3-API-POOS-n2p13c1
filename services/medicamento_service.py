import re
from typing import Any, List, Tuple

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
        if len(limpio) > 80:
            raise ValueError("El término de búsqueda no puede superar 80 caracteres.")
            
        return limpio

    @staticmethod
    def _primer_texto(
        valor: Any, predeterminado: str, limite: int = 200
    ) -> str:
        if isinstance(valor, str) and valor.strip():
            return valor.strip()[:limite]
        if isinstance(valor, list):
            for elemento in valor:
                if isinstance(elemento, str) and elemento.strip():
                    return elemento.strip()[:limite]
        return predeterminado

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
        
        params = {
            "search": (
                f'(openfda.brand_name:"{termino_seguro}" OR '
                f'openfda.generic_name:"{termino_seguro}")'
            ),
            "limit": 5,
        }
        if Settings.API_KEY:
            params["api_key"] = Settings.API_KEY

        try:
            # Siempre se define un timeout explícito para que el software no se congele
            response = requests.get(
                Settings.API_BASE_URL,
                headers=headers,
                params=params,
                timeout=Settings.REQUEST_TIMEOUT,
                verify=True
            )

            status_code = response.status_code
            if status_code == 404:
                return ([], f"No se encontraron medicamentos coincidentes con '{termino_seguro}'.")
            if status_code == 400:
                return ([], "La API rechazó la búsqueda por formato inválido.")
            if status_code == 401:
                return ([], "Error 401: Acceso no autorizado a la API externa.")
            if status_code == 403:
                return ([], "Error 403: La API denegó el acceso a la consulta.")
            if status_code == 408:
                return cls._manejar_contingencia(
                    termino_seguro, "La API agotó el tiempo de espera."
                )
            if status_code == 429:
                return ([], "Error 429: Límite de consultas a la API excedido.")
            if status_code >= 500:
                return ([], "Error del servidor externo. Intente nuevamente más tarde.")
            if status_code >= 400:
                return ([], f"La API rechazó la solicitud (HTTP {status_code}).")
            
            response.raise_for_status()
            try:
                data = response.json()
            except ValueError:
                return cls._manejar_contingencia(
                    termino_seguro,
                    "La API devolvió una respuesta JSON inválida.",
                )
            if not isinstance(data, dict):
                return ([], "La API devolvió una estructura JSON no esperada.")
            resultados = data.get("results", [])
            if not isinstance(resultados, list):
                return ([], "La API devolvió una lista de resultados no válida.")
            medicamentos: List[Medicamento] = []

            for item in resultados[:5]:
                if not isinstance(item, dict):
                    continue
                openfda = item.get("openfda", {})
                if not isinstance(openfda, dict):
                    openfda = {}
                nombre_generico = cls._primer_texto(
                    openfda.get("generic_name"), "No especificado"
                )
                nombre_comercial = cls._primer_texto(
                    openfda.get("brand_name"), nombre_generico
                )
                if nombre_comercial == "No especificado":
                    nombre_comercial = termino_seguro
                principio = cls._primer_texto(
                    openfda.get("substance_name"), nombre_generico
                )
                fabricante = cls._primer_texto(
                    openfda.get("manufacturer_name"), "No informado"
                )
                proposito = cls._primer_texto(
                    item.get("purpose"), "Uso terapéutico", limite=100
                )

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
        except requests.exceptions.RequestException:
            return cls._manejar_contingencia(
                termino_seguro,
                "Falla segura al comunicarse con el servicio externo.",
            )
        except (TypeError, ValueError):
            return cls._manejar_contingencia(
                termino_seguro,
                "Los datos recibidos no pudieron ser validados.",
            )

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
                timeout=Settings.REQUEST_TIMEOUT,
                verify=True
            )
            if resp.status_code in (200, 404):
                return (
                    True,
                    f"Conexión exitosa con el servicio externo "
                    f"(Código HTTP: {resp.status_code})",
                )
            return (False, f"El servicio respondió con HTTP {resp.status_code}.")
        except requests.exceptions.Timeout:
            return (False, "Timeout al contactar el servicio.")
        except requests.exceptions.ConnectionError:
            return (False, "Sin conexión de red hacia el servidor.")
        except requests.exceptions.RequestException:
            return (False, "Error seguro de red al contactar el servicio.")
        except (TypeError, ValueError):
            return (False, "No fue posible validar la respuesta del servicio.")