from typing import Optional, List

from views.utils import leer_numero, confirmar, leer_texto
from models.medicamento import Medicamento
from models.receta import Receta


class FarmaciaView:
    @staticmethod
    def mostrar_menu() -> int:
        print("\n" + "-" * 35)
        print("   FARMACIA Y RECETAS MÉDICAS")
        print("-" * 35)
        print("1.- Consultar medicamentos")
        print("2.- Prescribir medicamento a paciente")
        print("3.- Ver recetas de un paciente")
        print("4.- Listar todas las recetas")
        print("5.- Diagnosticar conexión con API")
        print("0.- Volver al menú principal")
        print("-" * 35)
        return leer_numero("Seleccione una opción: ")

    @staticmethod
    def pedir_termino_busqueda() -> str:
        return leer_texto("Ingrese nombre o principio activo (ej. 'aspirin', 'ibuprofen'): ")

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
        rut = leer_texto("Ingrese RUT del paciente receptor: ").upper()
        if not rut:
            print("Error: El RUT no puede quedar vacío.")
            return None

        dosis = leer_texto("Ingrese la dosis y posología (ej. '1 comprimido cada 8 hrs por 5 días'): ")
        if not dosis:
            print("Error: La dosis es obligatoria.")
            return None

        indicaciones = leer_texto("Indicaciones adicionales (opcional): ", permitir_vacio=True)

        if not confirmar("¿Confirma la emisión y guardado de esta receta médica?"):
            print("Operación cancelada.")
            return None

        return {
            "rut_paciente": rut,
            "dosis": dosis,
            "indicaciones": indicaciones,
        }

    @staticmethod
    def pedir_rut_busqueda() -> str:
        return leer_texto("\nIngrese el RUT del paciente a consultar: ", permitir_vacio=True).upper()

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
