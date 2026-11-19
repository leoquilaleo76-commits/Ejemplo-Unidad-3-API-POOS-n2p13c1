import hashlib
import unittest
from unittest.mock import Mock, patch

from models.usuario import Usuario
from services.medicamento_service import MedicamentoService, requests


class UsuarioSeguridadTests(unittest.TestCase):
    def test_hashes_pbkdf2_son_unicos_para_misma_clave(self) -> None:
        primera = Usuario.encriptar_credencial("ClaveSegura123")
        segunda = Usuario.encriptar_credencial("ClaveSegura123")
        self.assertTrue(primera.startswith("pbkdf2_sha256$"))
        self.assertNotEqual(primera, segunda)

    def test_verificacion_acepta_clave_correcta_y_rechaza_incorrecta(self) -> None:
        hash_valido = Usuario.encriptar_credencial("ClaveSegura123")
        usuario = Usuario("medico1", hash_valido, "Medico Uno")
        self.assertTrue(usuario.verificar_credencial("ClaveSegura123"))
        self.assertFalse(usuario.verificar_credencial("ClaveIncorrecta"))

    def test_credencial_corta_se_rechaza(self) -> None:
        with self.assertRaises(ValueError):
            Usuario.encriptar_credencial("corta")

    def test_hash_pbkdf2_rechaza_parametros_fuera_de_rango(self) -> None:
        with self.assertRaises(ValueError):
            Usuario(
                "medico1",
                f"pbkdf2_sha256$999999999${'a' * 32}${'b' * 64}",
                "Medico Uno",
            )

    def test_hash_legado_se_detecta_para_migracion(self) -> None:
        hash_legado = hashlib.sha256(b"admin1234").hexdigest()
        usuario = Usuario("admin", hash_legado, "Administrador")
        self.assertTrue(usuario.es_hash_legado())
        self.assertTrue(usuario.verificar_credencial("admin1234"))


class EntradaApiTests(unittest.TestCase):
    def test_sanitizador_rechaza_caracteres_maliciosos(self) -> None:
        with self.assertRaises(ValueError):
            MedicamentoService.sanitizar_termino("aspirin\" OR 1=1")

    def test_sanitizador_acepta_nombre_simple(self) -> None:
        self.assertEqual(
            MedicamentoService.sanitizar_termino("  ibuprofen  "),
            "ibuprofen",
        )

    def test_sanitizador_rechaza_busqueda_demasiado_larga(self) -> None:
        with self.assertRaises(ValueError):
            MedicamentoService.sanitizar_termino("a" * 81)

    @patch("services.medicamento_service.requests.get")
    def test_consulta_extrae_campos_json(self, get: Mock) -> None:
        respuesta = Mock()
        respuesta.status_code = 200
        respuesta.json.return_value = {
            "results": [{
                "openfda": {
                    "brand_name": ["Brand A"],
                    "generic_name": ["Generic A"],
                    "substance_name": ["Substance A"],
                    "manufacturer_name": ["Maker A"],
                },
                "purpose": ["Pain relief"],
            }]
        }
        get.return_value = respuesta

        medicamentos, mensaje = MedicamentoService.buscar_medicamentos("aspirin")

        self.assertEqual(len(medicamentos), 1)
        self.assertEqual(medicamentos[0].nombre_comercial, "Brand A")
        self.assertEqual(medicamentos[0].principio_activo, "Substance A")
        self.assertIn("1 medicamentos", mensaje)
        self.assertEqual(get.call_args.kwargs["timeout"], 5)
        self.assertTrue(get.call_args.kwargs["verify"])

    @patch("services.medicamento_service.Settings.API_KEY", "demo-key")
    @patch("services.medicamento_service.requests.get")
    def test_api_key_se_envia_como_parametro_de_openfda(self, get: Mock) -> None:
        respuesta = Mock()
        respuesta.status_code = 404
        get.return_value = respuesta

        MedicamentoService.buscar_medicamentos("aspirin")

        argumentos = get.call_args.kwargs
        self.assertEqual(argumentos["params"]["api_key"], "demo-key")
        self.assertNotIn("Authorization", argumentos["headers"])

    @patch("services.medicamento_service.requests.get")
    def test_codigos_http_se_muestran_con_mensajes_especificos(self, get: Mock) -> None:
        for codigo, texto in (
            (400, "formato inválido"),
            (401, "no autorizado"),
            (403, "denegó el acceso"),
            (404, "no se encontraron"),
            (408, "agotó el tiempo"),
            (429, "Límite"),
            (503, "servidor externo"),
            (418, "HTTP 418"),
        ):
            with self.subTest(codigo=codigo):
                respuesta = Mock()
                respuesta.status_code = codigo
                get.return_value = respuesta
                medicamentos, mensaje = MedicamentoService.buscar_medicamentos("aspirin")
                self.assertEqual(medicamentos, [])
                self.assertIn(texto.lower(), mensaje.lower())

    @patch("services.medicamento_service.Settings.ENABLE_OFFLINE_FALLBACK", True)
    @patch("services.medicamento_service.requests.get")
    def test_timeout_activa_contingencia_sin_interrumpir(self, get: Mock) -> None:
        get.side_effect = requests.exceptions.Timeout()

        medicamentos, mensaje = MedicamentoService.buscar_medicamentos("paracetamol")

        self.assertEqual(len(medicamentos), 1)
        self.assertIn("MODO CONTINGENCIA", mensaje)

    @patch("services.medicamento_service.requests.get")
    def test_json_malformado_no_expone_detalles_tecnicos(self, get: Mock) -> None:
        respuesta = Mock()
        respuesta.status_code = 200
        respuesta.json.side_effect = ValueError("private response detail")
        get.return_value = respuesta

        _, mensaje = MedicamentoService.buscar_medicamentos("aspirin")

        self.assertIn("JSON inválida", mensaje)
        self.assertNotIn("private response detail", mensaje)


if __name__ == "__main__":
    unittest.main()
