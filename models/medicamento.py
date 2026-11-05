class Medicamento:
    """Representa un medicamento obtenido desde la API externa o el catálogo local."""

    def __init__(
        self,
        nombre_comercial: str,
        nombre_generico: str = "",
        principio_activo: str = "",
        proposito: str = "",
        fabricante: str = "",
    ):
        self.nombre_comercial = nombre_comercial
        self.nombre_generico = nombre_generico
        self.principio_activo = principio_activo
        self.proposito = proposito
        self.fabricante = fabricante

    @property
    def nombre_comercial(self) -> str:
        return self._nombre_comercial

    @nombre_comercial.setter
    def nombre_comercial(self, valor: str) -> None:
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError("El nombre comercial del medicamento no puede estar vacío.")
        self._nombre_comercial = valor.strip()

    @property
    def nombre_generico(self) -> str:
        return self._nombre_generico

    @nombre_generico.setter
    def nombre_generico(self, valor: str) -> None:
        self._nombre_generico = valor.strip() if isinstance(valor, str) else ""

    @property
    def principio_activo(self) -> str:
        return self._principio_activo

    @principio_activo.setter
    def principio_activo(self, valor: str) -> None:
        self._principio_activo = valor.strip() if isinstance(valor, str) else ""

    @property
    def proposito(self) -> str:
        return self._proposito

    @proposito.setter
    def proposito(self, valor: str) -> None:
        self._proposito = valor.strip() if isinstance(valor, str) else ""

    @property
    def fabricante(self) -> str:
        return self._fabricante

    @fabricante.setter
    def fabricante(self, valor: str) -> None:
        self._fabricante = valor.strip() if isinstance(valor, str) else ""

    def __str__(self) -> str:
        return (
            f"{self.nombre_comercial} | Genérico: {self.nombre_generico or 'No especificado'} | "
            f"Principio activo: {self.principio_activo or 'No especificado'} | "
            f"Fabricante: {self.fabricante or 'No informado'}"
        )

    def __repr__(self) -> str:
        return (
            f"Medicamento(nombre_comercial='{self.nombre_comercial}', nombre_generico='{self.nombre_generico}', "
            f"principio_activo='{self.principio_activo}', proposito='{self.proposito}', fabricante='{self.fabricante}')"
        )
