from config.settings import Settings
from models.usuario import Usuario
from models.usuario_dao import UsuarioDAO
from views.auth_view import AuthView


class AuthController:
    """Controla el inicio de sesión y las operaciones de gestión de usuarios."""

    def __init__(self) -> None:
        self.view = AuthView()

    def iniciar_sesion(self) -> Usuario | None:
        UsuarioDAO.inicializar_admin_por_defecto()
        max_intentos = Settings.MAX_LOGIN_ATTEMPTS

        for intento in range(1, max_intentos + 1):
            self.view.mostrar_banner_login(intento, max_intentos)
            credenciales = self.view.solicitar_credenciales()
            username = credenciales["username"]
            clave = credenciales["clave"]

            es_valido, mensaje = Usuario.validar_credenciales_ingreso(username, clave)
            if not es_valido:
                self.view.mostrar_error(f"Validación fallida: {mensaje}")
                continue

            usuario = UsuarioDAO.obtener_por_username(username)
            if usuario is not None and usuario.verificar_credencial(clave):
                self.view.mostrar_bienvenida(usuario)
                return usuario

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
        es_valido, mensaje = Usuario.validar_credenciales_ingreso(
            datos["username"], datos["clave"]
        )
        if not es_valido:
            self.view.mostrar_error(mensaje)
            return
        if len(datos["nombre_completo"].strip()) < 3:
            self.view.mostrar_error(
                "El nombre completo no puede estar vacío y debe tener al menos 3 caracteres."
            )
            return
        if datos["clave"] != datos["confirmacion"]:
            self.view.mostrar_error("Las contraseñas ingresadas no coinciden.")
            return
        if UsuarioDAO.obtener_por_username(datos["username"]) is not None:
            self.view.mostrar_error(
                f"Ya existe un usuario registrado con el login '{datos['username']}'."
            )
            return

        try:
            nuevo_usuario = Usuario(
                username=datos["username"],
                password_hash=Usuario.encriptar_credencial(datos["clave"]),
                nombre_completo=datos["nombre_completo"],
                rol=datos["rol"],
            )
            if UsuarioDAO.crear(nuevo_usuario):
                self.view.mostrar_mensaje(
                    f"Usuario '{nuevo_usuario.username}' registrado exitosamente "
                    "con credencial encriptada."
                )
            else:
                self.view.mostrar_error(
                    "No fue posible guardar el usuario en la base de datos."
                )
        except (ValueError, TypeError) as error:
            self.view.mostrar_error(f"Datos inválidos: {error}")

    def listar_usuarios(self) -> None:
        self.view.mostrar_lista_usuarios(UsuarioDAO.obtener_todos())

    def eliminar_usuario(self, usuario_actual: Usuario | None = None) -> None:
        id_usuario = self.view.solicitar_id_usuario()
        usuario = UsuarioDAO.obtener_por_id(id_usuario)
        if usuario is None:
            self.view.mostrar_error("Usuario no encontrado.")
            return
        if usuario_actual and usuario.id_usuario == usuario_actual.id_usuario:
            self.view.mostrar_error(
                "No puede eliminar su propio usuario con la sesión activa."
            )
            return

        if self.view.confirmar_eliminacion(usuario.username):
            if UsuarioDAO.eliminar(id_usuario):
                self.view.mostrar_mensaje(
                    f"Usuario '{usuario.username}' eliminado exitosamente."
                )
            else:
                self.view.mostrar_error(
                    "Error al eliminar el usuario en la base de datos."
                )
        else:
            self.view.mostrar_mensaje("Operación cancelada.")
