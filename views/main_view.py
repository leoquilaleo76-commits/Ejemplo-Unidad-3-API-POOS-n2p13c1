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