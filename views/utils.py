def leer_numero(mensaje: str) -> int:
    while True:
        try:
            return int(input(mensaje))
        except EOFError:
            print("\n[INFO] Fin de entrada detectado. Se cerrará la operación actual.")
            return 0
        except ValueError:
            print("Error: Debe ingresar un número entero válido.")


def leer_texto(mensaje: str, permitir_vacio: bool = False) -> str:
    while True:
        try:
            valor = input(mensaje).strip()
        except EOFError:
            print("\n[INFO] Fin de entrada detectado. Se asumirá un valor vacío.")
            return ""
        if valor or permitir_vacio:
            return valor
        print("Error: Este campo no puede quedar vacío.")


def confirmar(mensaje: str) -> bool:
    while True:
        try:
            resp = input(f"{mensaje} (si/no): ").strip().lower()
        except EOFError:
            print("\n[INFO] Fin de entrada detectado. Se considera respuesta negativa.")
            return False
        if resp in ("si", "no"):
            return resp == "si"
        print("Respuesta no válida. Por favor, ingrese 'si' o 'no'.")