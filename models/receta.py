from datetime import datetime

class Receta:
    """
    Modelo de Dominio para una Receta Médica emitida.
    """
    def __init__(
        self,
        rut_paciente: str,
        nombre_medicamento: str,
        dosis: str,
        indicaciones: str = "",
        principio_activo: str = "",
        fecha_emision: str | None = None,
        id_receta: int | None = None
    ):
        self.id_receta = id_receta
        self.rut_paciente = rut_paciente
        self.nombre_medicamento = nombre_medicamento
        self.principio_activo = principio_activo
        self.dosis = dosis
        self.indicaciones = indicaciones
        self.fecha_emision = fecha_emision or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @property
    def rut_paciente(self) -> str:
        return self._rut_paciente

    @rut_paciente.setter
    def rut_paciente(self, valor: str) -> None:
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError("El RUT del paciente no puede estar vacío.")
        self._rut_paciente = valor.strip().upper()

    @property
    def nombre_medicamento(self) -> str:
        return self._nombre_medicamento

    @nombre_medicamento.setter
    def nombre_medicamento(self, valor: str) -> None:
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError("El nombre del medicamento no puede estar vacío.")
        self._nombre_medicamento = valor.strip().title()

    @property
    def dosis(self) -> str:
        return self._dosis

    @dosis.setter
    def dosis(self, valor: str) -> None:
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError("La dosis debe ser especificada (ej. '500 mg cada 8 horas').")
        self._dosis = valor.strip()

    def __str__(self) -> str:
        return (
            f"Receta #{self.id_receta or 'Nueva'} | Paciente: {self.rut_paciente} | "
            f"Fármaco: {self.nombre_medicamento} ({self.principio_activo}) | "
            f"Dosis: {self.dosis} | Fecha: {self.fecha_emision}"
        )