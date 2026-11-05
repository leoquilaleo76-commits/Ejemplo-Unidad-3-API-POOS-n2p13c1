# GUÍA DE IMPLEMENTACIÓN: INICIO DE SESIÓN CON CREDENCIALES ENCRIPTADAS Y VALIDACIÓN DE ENTRADAS
## Asignatura: Programación Orientada a Objeto Seguro (TI3021) – Semana 12
### Cómo evolucionar el proyecto de la Semana 11 agregando Autenticación Segura en MVC

---

## 1. OBJETIVO DE ESTA GUÍA

Esta guía explica paso a paso cómo tomar el proyecto de la **Semana 11** (*Sistema de Clínica con MVC, SQLite y Consumo de API OpenFDA*) e integrarle los dos nuevos requerimientos de seguridad de la **Semana 12**:

1. **Inicio de sesión mediante credenciales encriptadas:** Almacenamiento irreversible de contraseñas utilizando funciones criptográficas de resumen (**SHA-256** con `hashlib`) y comparación segura en tiempo constante (`hmac.compare_digest`), evitando guardar contraseñas en texto plano en la base de datos.
2. **Validación de credenciales ingresadas evitando valores vacíos o incorrectos:** Validación defensiva en capas (Vista, Controlador y Modelo con `@property`/`@setter`) que rechaza entradas vacías, cadenas de solo espacios, formatos inválidos o contraseñas erróneas, limitando además el número de intentos de acceso.

---

## 2. ARQUITECTURA DE AUTENTICACIÓN EN EL PATRÓN MVC + DAO

Para mantener intacta la arquitectura del proyecto anterior, el inicio de sesión se integra respetando la separación de responsabilidades:

```text
         [ USUARIO EN CONSOLA ]
                   │
                   ▼
        ┌─────────────────────┐
        │      AuthView       │ (views/auth_view.py)
        │  Pide usuario/clave │ -> Solo inputs y prints
        └──────────┬──────────┘
                   │
                   ▼
        ┌─────────────────────┐
        │   AuthController    │ (controllers/auth_controller.py)
        │ Controla intentos y │ -> Orquesta validación y acceso
        │ bloquea si falla    │
        └────┬───────────┬────┘
             │           │
             ▼           ▼
   ┌──────────────┐   ┌──────────────────┐
   │   Usuario    │   │    UsuarioDAO    │ (models/usuario_dao.py)
   │  (Modelo)    │   │  (SQLite CRUD)   │ -> Consultas parametrizadas (?)
   │  SHA-256 +   │   └────────┬─────────┘
   │  Validación  │            │
   └──────────────┘            ▼
                         [ clinica.db ]
                        (Tabla: usuario)
```

### Archivos Nuevos y Modificados respecto a la Semana 11

| Archivo | Estado | Propósito en el Proyecto |
| :--- | :--- | :--- |
| `.env` y `config/settings.py` | **Modificado** | Añade variables para el usuario administrador inicial y límite de intentos (`MAX_LOGIN_ATTEMPTS`). |
| `config/database.py` | **Modificado** | Crea la nueva tabla `usuario` en SQLite dentro de `init_db()`. |
| `models/usuario.py` | **Nuevo** | Modelo con validaciones `@property`, encriptación `SHA-256` y método `validar_credenciales_ingreso()`. |
| `models/usuario_dao.py` | **Nuevo** | DAO con consultas parametrizadas (`?`) y creación automática del administrador inicial. |
| `views/auth_view.py` | **Nuevo** | Pantalla de login y submenú de gestión de usuarios. |
| `controllers/auth_controller.py` | **Nuevo** | Controla el flujo de login, valida vacíos/incorrectos y gestiona usuarios. |
| `views/main_view.py` | **Modificado** | Muestra el usuario en sesión activa, opción `4.- Gestión de Usuarios` y `9.- Cerrar Sesión`. |
| `controllers/main_controller.py` | **Modificado** | Exige superar `auth_controller.iniciar_sesion()` antes de mostrar el menú principal. |

---

## 3. PASO A PASO PARA IMPLEMENTARLO EN EL PROYECTO DE LA SEMANA 11

---

### PASO 1: Actualizar `.env` y `config/settings.py`

Para no dejar credenciales escritas en duro dentro del código fuente (lo que activaría la alerta **B105** en **Bandit**), declaramos los datos del usuario inicial en el archivo `.env`.

1. Abre tu archivo `.env` y agrega al final:
```env
# Configuración de Autenticación Inicial (Semana 12)
ADMIN_INITIAL_USER=admin
ADMIN_INITIAL_CLAVE=admin1234
MAX_LOGIN_ATTEMPTS=3
```

2. Abre `config/settings.py` y agrega la lectura de estas tres variables dentro de la clase `Settings`:
```python
    # Parámetros para inicio de sesión y semilla de usuario administrador
    ADMIN_INITIAL_USER: str = os.getenv("ADMIN_INITIAL_USER", "admin")
    ADMIN_INITIAL_CLAVE: str = os.getenv("ADMIN_INITIAL_CLAVE", "admin1234")
    MAX_LOGIN_ATTEMPTS: int = int(os.getenv("MAX_LOGIN_ATTEMPTS", "3"))
```

---

### PASO 2: Agregar la tabla `usuario` en `config/database.py`

Abre `config/database.py` y, dentro del método `init_db()`, agrega la sentencia `CREATE TABLE IF NOT EXISTS usuario` antes o después de las tablas existentes:

```python
            # Tabla Usuario (Semana 12: Inicio de sesión con credenciales encriptadas)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuario (
                    id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    nombre_completo TEXT NOT NULL,
                    rol TEXT NOT NULL
                )
            """)
```

> [!IMPORTANT]
> Observa que la columna se llama `password_hash` y **no** `password`. Nunca almacenamos la contraseña original en la base de datos, únicamente su resumen criptográfico de 64 caracteres hexadecimales.

---

### PASO 3: Crear el Modelo `Usuario` (`models/usuario.py`)

Crea el archivo `models/usuario.py`. Esta clase concentra tanto la **encriptación SHA-256** como la **validación estricta contra valores vacíos o incorrectos**:

```python
import hashlib
import hmac
import re

class Usuario:
    """
    Modelo de Dominio para la entidad Usuario.
    Implementa:
    - Encriptación irreversible de credenciales mediante SHA-256 (hashlib).
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
        if len(limpio) != 64 or not re.match(r"^[a-f0-9]{64}$", limpio):
            raise ValueError("La credencial debe almacenarse como un hash SHA-256 válido de 64 caracteres hexadecimales.")
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
        """
        Valida que la contraseña en texto plano no esté vacía ni sea demasiado corta,
        y retorna su representación encriptada mediante el algoritmo criptográfico SHA-256.
        """
        if not isinstance(clave_plana, str) or not clave_plana.strip():
            raise ValueError("La contraseña no puede estar vacía ni contener solo espacios.")
        clave_limpia = clave_plana.strip()
        if len(clave_limpia) < 4:
            raise ValueError("La contraseña debe tener al menos 4 caracteres.")
        return hashlib.sha256(clave_limpia.encode("utf-8")).hexdigest()

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
        if len(clave_limpia) < 4:
            return (False, "La contraseña ingresada es inválida (mínimo 4 caracteres).")

        return (True, "Formato de credenciales válido.")

    def verificar_credencial(self, clave_ingresada: str) -> bool:
        """
        Compara la contraseña ingresada (en texto plano) con el hash encriptado del usuario
        utilizando comparación en tiempo constante para mitigar ataques de temporización.
        """
        if not isinstance(clave_ingresada, str) or not clave_ingresada.strip():
            return False
        try:
            hash_ingresado = self.encriptar_credencial(clave_ingresada)
            return hmac.compare_digest(self._password_hash, hash_ingresado)
        except ValueError:
            return False

    def __str__(self) -> str:
        id_str = self.id_usuario if self.id_usuario is not None else "Nuevo"
        hash_resumen = f"{self.password_hash[:12]}...{self.password_hash[-6:]}"
        return (
            f"Usuario [ID: {id_str}] | Login: {self.username} | "
            f"Nombre: {self.nombre_completo} | Rol: {self.rol} | Hash SHA-256: {hash_resumen}"
        )
```

---

### PASO 4: Crear el DAO de Usuarios (`models/usuario_dao.py`)

Crea el archivo `models/usuario_dao.py` para persistir y consultar usuarios en SQLite usando consultas parametrizadas (`?`):

```python
import sqlite3
from sqlite3 import Cursor
from config.database import Database
from config.settings import Settings
from models.usuario import Usuario

class UsuarioDAO:
    """
    Data Access Object para la entidad Usuario.
    Gestiona la persistencia de cuentas y credenciales encriptadas en SQLite
    utilizando consultas parametrizadas (?) contra SQL Injection (Bandit B608).
    """

    @staticmethod
    def crear(usuario: Usuario) -> bool:
        conn = Database().get_connection()
        try:
            cursor: Cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO usuario (username, password_hash, nombre_completo, rol) VALUES (?, ?, ?, ?)",
                (usuario.username, usuario.password_hash, usuario.nombre_completo, usuario.rol)
            )
            conn.commit()
            usuario.id_usuario = cursor.lastrowid
            return True
        except sqlite3.IntegrityError:
            print(f"Error: El nombre de usuario '{usuario.username}' ya se encuentra registrado.")
            return False
        except sqlite3.Error as e:
            print(f"Error al crear usuario en BD: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def obtener_por_username(username: str) -> Usuario | None:
        if not isinstance(username, str) or not username.strip():
            return None
        conn = Database().get_connection()
        usuario = None
        try:
            cursor: Cursor = conn.cursor()
            cursor.execute(
                "SELECT id_usuario, username, password_hash, nombre_completo, rol FROM usuario WHERE username = ?",
                (username.strip().lower(),)
            )
            fila = cursor.fetchone()
            if fila:
                usuario = Usuario(
                    username=fila["username"],
                    password_hash=fila["password_hash"],
                    nombre_completo=fila["nombre_completo"],
                    rol=fila["rol"],
                    id_usuario=fila["id_usuario"]
                )
        except sqlite3.Error as e:
            print(f"Error al consultar usuario: {e}")
        finally:
            conn.close()
        return usuario

    @staticmethod
    def obtener_por_id(id_usuario: int) -> Usuario | None:
        conn = Database().get_connection()
        usuario = None
        try:
            cursor: Cursor = conn.cursor()
            cursor.execute(
                "SELECT id_usuario, username, password_hash, nombre_completo, rol FROM usuario WHERE id_usuario = ?",
                (id_usuario,)
            )
            fila = cursor.fetchone()
            if fila:
                usuario = Usuario(
                    username=fila["username"],
                    password_hash=fila["password_hash"],
                    nombre_completo=fila["nombre_completo"],
                    rol=fila["rol"],
                    id_usuario=fila["id_usuario"]
                )
        except sqlite3.Error as e:
            print(f"Error al obtener usuario por ID: {e}")
        finally:
            conn.close()
        return usuario

    @staticmethod
    def obtener_todos() -> list[Usuario]:
        conn = Database().get_connection()
        usuarios: list[Usuario] = []
        try:
            cursor: Cursor = conn.cursor()
            cursor.execute(
                "SELECT id_usuario, username, password_hash, nombre_completo, rol FROM usuario ORDER BY id_usuario ASC"
            )
            for fila in cursor.fetchall():
                usuarios.append(
                    Usuario(
                        username=fila["username"],
                        password_hash=fila["password_hash"],
                        nombre_completo=fila["nombre_completo"],
                        rol=fila["rol"],
                        id_usuario=fila["id_usuario"]
                    )
                )
        except sqlite3.Error as e:
            print(f"Error al listar usuarios: {e}")
        finally:
            conn.close()
        return usuarios

    @staticmethod
    def eliminar(id_usuario: int) -> bool:
        conn = Database().get_connection()
        try:
            cursor: Cursor = conn.cursor()
            cursor.execute("DELETE FROM usuario WHERE id_usuario = ?", (id_usuario,))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error al eliminar usuario: {e}")
            return False
        finally:
            conn.close()

    @classmethod
    def inicializar_admin_por_defecto(cls) -> None:
        """
        Si la tabla está vacía, crea un usuario Administrador inicial con su
        contraseña encriptada (SHA-256) a partir de la configuración del entorno.
        """
        usuarios_existentes = cls.obtener_todos()
        if not usuarios_existentes:
            try:
                hash_inicial = Usuario.encriptar_credencial(Settings.ADMIN_INITIAL_CLAVE)
                admin_default = Usuario(
                    username=Settings.ADMIN_INITIAL_USER,
                    password_hash=hash_inicial,
                    nombre_completo="Administrador Del Sistema",
                    rol="Administrador"
                )
                cls.crear(admin_default)
            except ValueError as e:
                print(f"Error al inicializar el usuario administrador por defecto: {e}")
```

---

### PASO 5: Crear la Vista de Autenticación (`views/auth_view.py`)

Crea el archivo `views/auth_view.py` para solicitar las credenciales en consola y gestionar usuarios:

```python
from views.utils import leer_numero, confirmar
from models.usuario import Usuario

class AuthView:
    """
    Vista de consola para el Inicio de Sesión y la Gestión de Usuarios con Credenciales Encriptadas.
    """

    @staticmethod
    def mostrar_banner_login(intento_actual: int, max_intentos: int) -> None:
        print("\n" + "=" * 55)
        print("   CLÍNICA SANITARIA - INICIO DE SESIÓN SEGURO (SHA-256)")
        print("=" * 55)
        print(f"Intento {intento_actual} de {max_intentos} (Por defecto: admin / admin1234)")
        print("-" * 55)

    @staticmethod
    def solicitar_credenciales() -> dict:
        username = input("Usuario    : ").strip()
        clave = input("Contraseña : ").strip()
        return {
            "username": username,
            "clave": clave
        }

    @staticmethod
    def mostrar_bienvenida(usuario: Usuario) -> None:
        print("\n" + "*" * 55)
        print(f"  [ACCESO CONCEDIDO] Bienvenido/a, {usuario.nombre_completo}")
        print(f"  Usuario: {usuario.username} | Rol: {usuario.rol}")
        print("*" * 55)

    @staticmethod
    def mostrar_menu_usuarios() -> int:
        print("\n" + "-" * 45)
        print("   GESTIÓN DE USUARIOS Y CREDENCIALES")
        print("-" * 45)
        print("1.- Registrar nuevo usuario (Encriptar clave)")
        print("2.- Listar usuarios y verificar hashes SHA-256")
        print("3.- Eliminar usuario")
        print("0.- Volver al menú principal")
        print("-" * 45)
        return leer_numero("Seleccione una opción: ")

    @staticmethod
    def formulario_nuevo_usuario() -> dict:
        print("\n--- Registrar Nuevo Usuario ---")
        username = input("Ingrese nombre de usuario (mín. 3 caracteres, sin espacios): ").strip()
        nombre_completo = input("Ingrese nombre completo del funcionario: ").strip()
        clave = input("Ingrese contraseña (mín. 4 caracteres, se encriptará con SHA-256): ").strip()
        confirmacion = input("Confirme la contraseña: ").strip()

        print("Roles disponibles: 1.- Administrador, 2.- Medico, 3.- Operador")
        opcion_rol = leer_numero("Seleccione un rol (1-3): ")
        mapa_roles = {1: "Administrador", 2: "Medico", 3: "Operador"}
        rol = mapa_roles.get(opcion_rol, "")

        return {
            "username": username,
            "nombre_completo": nombre_completo,
            "clave": clave,
            "confirmacion": confirmacion,
            "rol": rol
        }

    @staticmethod
    def mostrar_lista_usuarios(usuarios: list[Usuario]) -> None:
        print("\n--- Lista de Usuarios Registrados (Credenciales Encriptadas) ---")
        if not usuarios:
            print("No hay usuarios registrados.")
        else:
            for u in usuarios:
                print(u)
        print("-" * 64)

    @staticmethod
    def solicitar_id_usuario() -> int:
        return leer_numero("Ingrese el ID del usuario a eliminar: ")

    @staticmethod
    def confirmar_eliminacion(username: str) -> bool:
        return confirmar(f"¿Está seguro que desea eliminar al usuario '{username}'?")

    @staticmethod
    def mostrar_mensaje(mensaje: str) -> None:
        print(f"\n[AUTENTICACIÓN] {mensaje}")

    @staticmethod
    def mostrar_error(error: str) -> None:
        print(f"\n[ERROR DE CREDENCIALES] {error}")
```

---

### PASO 6: Crear el Controlador de Autenticación (`controllers/auth_controller.py`)

Crea el archivo `controllers/auth_controller.py` para coordinar la validación de entradas, la encriptación y el límite de intentos:

```python
from config.settings import Settings
from models.usuario import Usuario
from models.usuario_dao import UsuarioDAO
from views.auth_view import AuthView

class AuthController:
    """
    Controlador de Autenticación y Gestión de Usuarios.
    Orquesta el inicio de sesión validando que las credenciales no estén vacías
    ni sean incorrectas, y comparando contraseñas mediante hashes SHA-256.
    """

    def __init__(self):
        self.view = AuthView()

    def iniciar_sesion(self) -> Usuario | None:
        """
        Ejecuta el flujo de inicio de sesión antes de permitir el acceso al menú principal.
        Retorna la instancia de Usuario autenticado o None si agota los intentos.
        """
        UsuarioDAO.inicializar_admin_por_defecto()
        max_intentos = Settings.MAX_LOGIN_ATTEMPTS

        for intento in range(1, max_intentos + 1):
            self.view.mostrar_banner_login(intento, max_intentos)
            credenciales = self.view.solicitar_credenciales()
            username = credenciales["username"]
            clave = credenciales["clave"]

            # 1. Validar que las credenciales ingresadas no estén vacías ni tengan formato inválido
            es_valido, mensaje_validacion = Usuario.validar_credenciales_ingreso(username, clave)
            if not es_valido:
                self.view.mostrar_error(f"Validación fallida: {mensaje_validacion}")
                continue

            # 2. Buscar el usuario en la base de datos y verificar su credencial encriptada
            usuario_bd = UsuarioDAO.obtener_por_username(username)
            if usuario_bd is not None and usuario_bd.verificar_credencial(clave):
                self.view.mostrar_bienvenida(usuario_bd)
                return usuario_bd

            self.view.mostrar_error(
                "Credenciales incorrectas: el usuario no existe o la contraseña no coincide."
            )

        self.view.mostrar_error(
            f"Ha superado el número máximo de intentos permitidos ({max_intentos}). "
            "Acceso bloqueado por seguridad."
        )
        return None

    def ejecutar(self, usuario_actual: Usuario | None = None) -> None:
        while True:
            opcion = self.view.mostrar_menu_usuarios()
            if opcion == 1:
                self.registrar_usuario()
            elif opcion == 2:
                self.listar_usuarios()
            elif opcion == 3:
                self.eliminar_usuario(usuario_actual)
            elif opcion == 0:
                self.view.mostrar_mensaje("Saliendo de la gestión de usuarios.")
                break
            else:
                self.view.mostrar_error("Opción no válida.")

    def registrar_usuario(self) -> None:
        datos = self.view.formulario_nuevo_usuario()

        es_valido, msg = Usuario.validar_credenciales_ingreso(datos["username"], datos["clave"])
        if not es_valido:
            self.view.mostrar_error(msg)
            return

        if not datos["nombre_completo"]:
            self.view.mostrar_error("El nombre completo no puede estar vacío.")
            return

        if datos["clave"] != datos["confirmacion"]:
            self.view.mostrar_error("Las contraseñas ingresadas no coinciden.")
            return

        if UsuarioDAO.obtener_por_username(datos["username"]):
            self.view.mostrar_error(f"Ya existe un usuario registrado con el login '{datos['username']}'.")
            return

        try:
            password_encriptada = Usuario.encriptar_credencial(datos["clave"])
            nuevo_usuario = Usuario(
                username=datos["username"],
                password_hash=password_encriptada,
                nombre_completo=datos["nombre_completo"],
                rol=datos["rol"]
            )
            if UsuarioDAO.crear(nuevo_usuario):
                self.view.mostrar_mensaje(
                    f"Usuario '{nuevo_usuario.username}' registrado exitosamente con credencial encriptada."
                )
            else:
                self.view.mostrar_error("No fue posible guardar el usuario en la base de datos.")
        except (ValueError, TypeError) as e:
            self.view.mostrar_error(f"Datos inválidos: {e}")

    def listar_usuarios(self) -> None:
        usuarios = UsuarioDAO.obtener_todos()
        self.view.mostrar_lista_usuarios(usuarios)

    def eliminar_usuario(self, usuario_actual: Usuario | None = None) -> None:
        id_usuario = self.view.solicitar_id_usuario()
        usuario = UsuarioDAO.obtener_por_id(id_usuario)
        if not usuario:
            self.view.mostrar_error("Usuario no encontrado.")
            return

        if usuario_actual and usuario.id_usuario == usuario_actual.id_usuario:
            self.view.mostrar_error("No puede eliminar su propio usuario con la sesión activa.")
            return

        if self.view.confirmar_eliminacion(usuario.username):
            if UsuarioDAO.eliminar(id_usuario):
                self.view.mostrar_mensaje(f"Usuario '{usuario.username}' eliminado exitosamente.")
            else:
                self.view.mostrar_error("Error al eliminar el usuario en la base de datos.")
        else:
            self.view.mostrar_mensaje("Operación cancelada.")
```

---

### PASO 7: Integrar el Inicio de Sesión en `MainView` y `MainController`

1. Actualiza `views/main_view.py` para mostrar el usuario autenticado y las opciones de gestión de usuarios y cierre de sesión:

```python
from views.utils import leer_numero
from models.usuario import Usuario

class MainView:
    @staticmethod
    def mostrar_menu(usuario_actual: Usuario | None = None) -> int:
        print("\n" + "=" * 55)
        print("     CLÍNICA SANITARIA - MENÚ PRINCIPAL (U3)")
        if usuario_actual:
            print(f"     Sesión activa: {usuario_actual.username} ({usuario_actual.rol})")
        print("=" * 55)
        print("1.- Gestión de Pacientes")
        print("2.- Gestión de Departamentos")
        print("3.- Farmacia y Recetas Médicas (Consumo API U3)")
        print("4.- Gestión de Usuarios (Credenciales Encriptadas)")
        print("9.- Cerrar Sesión (Cambiar de Usuario)")
        print("0.- Salir del Sistema")
        print("=" * 55)
        return leer_numero("Seleccione una opción: ")

    @staticmethod
    def mostrar_mensaje(mensaje: str) -> None:
        print(f"\n[SISTEMA] {mensaje}")
```

2. Actualiza `controllers/main_controller.py` para exigir el inicio de sesión antes de entrar al menú:

```python
from views.main_view import MainView
from controllers.auth_controller import AuthController
from controllers.paciente_controller import PacienteController
from controllers.departamento_controller import DepartamentoController
from controllers.farmacia_controller import FarmaciaController
from models.usuario import Usuario

class MainController:
    def __init__(self):
        self.view = MainView()
        self.auth_controller = AuthController()
        self.paciente_controller = PacienteController()
        self.departamento_controller = DepartamentoController()
        self.farmacia_controller = FarmaciaController()
        self.usuario_actual: Usuario | None = None

    def ejecutar(self) -> None:
        # 1. Solicitar inicio de sesión con credenciales encriptadas antes de entrar al sistema
        self.usuario_actual = self.auth_controller.iniciar_sesion()
        if not self.usuario_actual:
            self.view.mostrar_mensaje("El programa ha finalizado debido a credenciales inválidas.")
            return

        # 2. Bucle principal de la aplicación una vez autenticado
        while True:
            opcion = self.view.mostrar_menu(self.usuario_actual)
            if opcion == 1:
                self.paciente_controller.ejecutar()
            elif opcion == 2:
                self.departamento_controller.ejecutar()
            elif opcion == 3:
                self.farmacia_controller.ejecutar()
            elif opcion == 4:
                self.auth_controller.ejecutar(self.usuario_actual)
            elif opcion == 9:
                self.view.mostrar_mensaje(f"Cerrando sesión de '{self.usuario_actual.username}'...")
                self.usuario_actual = self.auth_controller.iniciar_sesion()
                if not self.usuario_actual:
                    self.view.mostrar_mensaje("El programa ha finalizado debido a credenciales inválidas.")
                    break
            elif opcion == 0:
                self.view.mostrar_mensaje("Gracias por usar el sistema de la Clínica. ¡Hasta luego!")
                break
            else:
                self.view.mostrar_mensaje("Opción no válida. Por favor, intente nuevamente.")
```

---

## 4. CÓMO PROBAR LA IMPLEMENTACIÓN Y LAS VALIDACIONES

1. Ejecuta el sistema desde la terminal:
   ```bash
   python main.py
   ```
