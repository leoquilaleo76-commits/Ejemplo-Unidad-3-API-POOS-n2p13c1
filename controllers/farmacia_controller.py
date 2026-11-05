from views.farmacia_view import FarmaciaView
from services.medicamento_service import MedicamentoService
from models.receta import Receta
from models.receta_dao import RecetaDAO
from models.paciente_dao import PacienteDAO


class FarmaciaController:
    """Controlador que orquesta la vista, el servicio externo y la persistencia local."""

    def __init__(self):
        self.view = FarmaciaView()
        self.service = MedicamentoService()
        self.receta_dao = RecetaDAO()
        self.paciente_dao = PacienteDAO()

    def ejecutar(self) -> None:
        while True:
            opcion = self.view.mostrar_menu()
            if opcion == 1:
                self.consultar_medicamentos()
            elif opcion == 2:
                self.prescribir_medicamento()
            elif opcion == 3:
                self.consultar_recetas_paciente()
            elif opcion == 4:
                self.listar_todas_recetas()
            elif opcion == 5:
                self.diagnosticar_conexion()
            elif opcion == 0:
                break
            else:
                self.view.mostrar_error("Opción no válida. Intente nuevamente.")

    def consultar_medicamentos(self) -> None:
        termino = self.view.pedir_termino_busqueda()
        if not termino:
            return
        try:
            medicamentos, estado = self.service.buscar_medicamentos(termino)
            self.view.mostrar_mensaje(estado)
            self.view.mostrar_medicamentos(medicamentos)
        except ValueError as e:
            self.view.mostrar_error(str(e))
        except Exception as e:
            self.view.mostrar_error(f"Error inesperado: {str(e)}")

    def prescribir_medicamento(self) -> None:
        termino = self.view.pedir_termino_busqueda()
        if not termino:
            return

        try:
            medicamentos, estado = self.service.buscar_medicamentos(termino)
            self.view.mostrar_mensaje(estado)
            if not medicamentos:
                return

            self.view.mostrar_medicamentos(medicamentos)
            med_seleccionado = self.view.seleccionar_medicamento(medicamentos)
            if not med_seleccionado:
                return

            datos_receta = self.view.pedir_datos_receta(med_seleccionado)
            if not datos_receta:
                return

            rut = datos_receta["rut_paciente"]
            paciente = self.paciente_dao.obtener_por_rut(rut)
            if not paciente:
                self.view.mostrar_error(
                    f"El paciente con RUT '{rut}' no está registrado en el sistema. "
                    "Debe registrarlo primero en el módulo de Pacientes antes de recetar."
                )
                return

            nueva_receta = Receta(
                rut_paciente=rut,
                nombre_medicamento=med_seleccionado.nombre_comercial,
                principio_activo=med_seleccionado.principio_activo,
                dosis=datos_receta["dosis"],
                indicaciones=datos_receta["indicaciones"],
            )

            id_generado = self.receta_dao.insertar(nueva_receta)
            if id_generado:
                nueva_receta.id_receta = id_generado
                self.view.mostrar_mensaje(
                    f"¡Receta #{id_generado} emitida y guardada con éxito en SQLite!\n"
                    f"Paciente: {paciente.nombre} ({paciente.rut}) | Medicamento: {nueva_receta.nombre_medicamento}"
                )
            else:
                self.view.mostrar_error("No se pudo guardar la receta en la base de datos.")

        except ValueError as e:
            self.view.mostrar_error(str(e))
        except Exception as e:
            self.view.mostrar_error(f"Error al emitir receta: {str(e)}")

    def consultar_recetas_paciente(self) -> None:
        rut = self.view.pedir_rut_busqueda()
        if not rut:
            return
        recetas = self.receta_dao.obtener_por_paciente(rut)
        self.view.mostrar_recetas(recetas)

    def listar_todas_recetas(self) -> None:
        recetas = self.receta_dao.listar_todas()
        self.view.mostrar_recetas(recetas)

    def diagnosticar_conexion(self) -> None:
        self.view.mostrar_mensaje("Verificando conectividad con el servicio externo...")
        exito, detalle = self.service.probar_conectividad()
        if exito:
            self.view.mostrar_mensaje(f"[ONLINE] {detalle}")
        else:
            self.view.mostrar_error(f"[OFFLINE] {detalle}")
