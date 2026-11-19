import hashlib
import hmac
import os
import re

class Usuario:
    """
    Modelo de Dominio para la entidad Usuario.
    Implementa:
    - Derivación de contraseñas con PBKDF2-HMAC-SHA256 y salt aleatorio.
    - Comparación segura en tiempo constante (hmac.compare_digest).
    - Validación defensiva con @property y @setter evitando valores vacíos o incorrectos.
    """
    ROLES: set[str] = {"Administrador", "Medico", "Operador"}

    def __init__(
        self,
        username: str,
        password_hash: str,
        nombre_completo: str,
        rol: str = "Operador",
        id_usuario: int | None = None
    ):
        self.id_usuario = id_usuario
        self.username = username
        self.password_hash = password_hash
        self.nombre_completo = nombre_completo
        self.rol = rol

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, valor: str) -> None:
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError("El nombre de usuario no puede estar vacío.")
        limpio = valor.strip().lower()
        if len(limpio) < 3:
            raise ValueError("El nombre de usuario debe tener al menos 3 caracteres.")
        if not re.match(r"^[a-zA-Z0-9_.-]+$", limpio):
            raise ValueError("El nombre de usuario solo puede contener letras, números, puntos, guiones o guiones bajos.")
        self._username = limpio

    @property
    def password_hash(self) -> str:
        return self._password_hash

    @password_hash.setter
    def password_hash(self, valor: str) -> None:
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError("El hash de la contraseña no puede estar vacío.")
        limpio = valor.strip().lower()
        coincidencia_pbkdf2 = re.match(
            r"^pbkdf2_sha256\$(\d+)\$[a-f0-9]{32}\$[a-f0-9]{64}$",
            limpio,
        )
        es_pbkdf2 = bool(
            coincidencia_pbkdf2
            and 100_000 <= int(coincidencia_pbkdf2.group(1)) <= 1_000_000
        )
        es_legado = len(limpio) == 64 and bool(re.match(r"^[a-f0-9]{64}$", limpio))
        if not es_pbkdf2 and not es_legado:
            raise ValueError("La credencial almacenada tiene un formato de hash no soportado.")
        self._password_hash = limpio

    @property
    def nombre_completo(self) -> str:
        return self._nombre_completo

    @nombre_completo.setter
    def nombre_completo(self, valor: str) -> None:
        if not isinstance(valor, str) or len(valor.strip()) < 3:
            raise ValueError("El nombre completo no puede estar vacío y debe tener al menos 3 caracteres.")
        self._nombre_completo = valor.strip().title()

    @property
    def rol(self) -> str:
        return self._rol

    @rol.setter
    def rol(self, valor: str) -> None:
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError("El rol del usuario no puede estar vacío.")
        rol_limpio = valor.strip().capitalize()
        if rol_limpio not in self.ROLES:
            opciones = ", ".join(sorted(self.ROLES))
            raise ValueError(f"Rol '{valor}' no válido. Opciones permitidas: {opciones}.")
        self._rol = rol_limpio

    @staticmethod
    def encriptar_credencial(clave_plana: str) -> str:
        """Genera una credencial PBKDF2 con salt aleatorio."""
        if not isinstance(clave_plana, str) or not clave_plana.strip():
            raise ValueError("La contraseña no puede estar vacía ni contener solo espacios.")
        clave_limpia = clave_plana.strip()
        if len(clave_limpia) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres.")
        iteraciones = 200_000
        salt = os.urandom(16)
        derivado = hashlib.pbkdf2_hmac(
            "sha256", clave_limpia.encode("utf-8"), salt, iteraciones
        )
        return f"pbkdf2_sha256${iteraciones}${salt.hex()}${derivado.hex()}"

    def es_hash_legado(self) -> bool:
        return len(self._password_hash) == 64

    @staticmethod
    def validar_credenciales_ingreso(username: str, clave_plana: str) -> tuple[bool, str]:
        """
        Valida las credenciales ingresadas por el usuario antes de procesar el login,
        evitando valores vacíos o con formato incorrecto.
        """
        if not isinstance(username, str) or not username.strip():
            return (False, "El campo 'Usuario' no puede estar vacío.")
        if not isinstance(clave_plana, str) or not clave_plana.strip():
            return (False, "El campo 'Contraseña' no puede estar vacío.")

        user_limpio = username.strip()
        clave_limpia = clave_plana.strip()

        if len(user_limpio) < 3:
            return (False, "El nombre de usuario ingresado es inválido (mínimo 3 caracteres).")
        if not re.match(r"^[a-zA-Z0-9_.-]+$", user_limpio):
            return (False, "El nombre de usuario contiene caracteres no permitidos.")
        if len(clave_limpia) < 8:
            return (False, "La contraseña ingresada es inválida (mínimo 8 caracteres).")

        return (True, "Formato de credenciales válido.")

    def verificar_credencial(self, clave_ingresada: str) -> bool:
        if not isinstance(clave_ingresada, str) or not clave_ingresada.strip():
            return False
        try:
            if self.es_hash_legado():
                hash_ingresado = hashlib.sha256(
                    clave_ingresada.strip().encode("utf-8")
                ).hexdigest()
            else:
                _, iteraciones, salt_hex, hash_esperado = self._password_hash.split("$")
                derivado = hashlib.pbkdf2_hmac(
                    "sha256",
                    clave_ingresada.strip().encode("utf-8"),
                    bytes.fromhex(salt_hex),
                    int(iteraciones),
                )
                hash_ingresado = derivado.hex()
                return hmac.compare_digest(hash_esperado, hash_ingresado)
            return hmac.compare_digest(self._password_hash, hash_ingresado)
        except (ValueError, TypeError):
            return False

    def __str__(self) -> str:
        id_str = self.id_usuario if self.id_usuario is not None else "Nuevo"
        hash_resumen = f"{self.password_hash[:12]}...{self.password_hash[-6:]}"
        return (
            f"Usuario [ID: {id_str}] | Login: {self.username} | "
            f"Nombre: {self.nombre_completo} | Rol: {self.rol} | Hash PBKDF2: {hash_resumen}"
        )
        