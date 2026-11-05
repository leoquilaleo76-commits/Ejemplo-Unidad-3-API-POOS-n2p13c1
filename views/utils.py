def leer_texto(mensaje: str, *, permitir_vacio: bool = True) -> str:
    while True:
        try:
            valor = input(mensaje)
        except (EOFError, KeyboardInterrupt):
            print("\n[INFO] Se canceló la entrada por teclado. Cerrando la aplicación.")
            raise SystemExit(0)

        valor = valor.strip()
        if valor or permitir_vacio:
            return valor
        print("Este campo no puede quedar vacío.")


def leer_numero(mensaje: str) -> int:
    while True:
        try:
            return int(leer_texto(mensaje))
        except ValueError:
            print("Error: Debe ingresar un número entero válido.")
        except SystemExit:
            raise


def confirmar(mensaje: str) -> bool:
    while True:
        try:
            resp = leer_texto(f"{mensaje} (si/no): ").lower()
        except SystemExit:
            raise

        if resp in ("si", "no"):
            return resp == "si"
        print("Respuesta no válida. Por favor, ingrese 'si' o 'no'.")
