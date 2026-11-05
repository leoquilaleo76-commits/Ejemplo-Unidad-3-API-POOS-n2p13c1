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