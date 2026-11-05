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
        self.usuario_actual = self.auth_controller.iniciar_sesion()
        if self.usuario_actual is None:
            self.view.mostrar_mensaje("El programa ha finalizado debido a credenciales inválidas.")
            return

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
                self.view.mostrar_mensaje(
                    f"Cerrando sesión de '{self.usuario_actual.username}'..."
                )
                self.usuario_actual = self.auth_controller.iniciar_sesion()
                if self.usuario_actual is None:
                    self.view.mostrar_mensaje(
                        "El programa ha finalizado debido a credenciales inválidas."
                    )
                    break
            elif opcion == 0:
                self.view.mostrar_mensaje("Gracias por usar el sistema de la Clínica. ¡Hasta luego!")
                break
            else:
                self.view.mostrar_mensaje("Opción no válida. Por favor, intente nuevamente.")
