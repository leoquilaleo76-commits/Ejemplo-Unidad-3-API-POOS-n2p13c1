import sqlite3
from typing import List, Optional
from config.database import Database
from models.receta import Receta

class RecetaDAO:
    """
    Data Access Object para la persistencia local de recetas médicas en SQLite.
    """
    def __init__(self):
        self.db = Database()

    def insertar(self, receta: Receta) -> Optional[int]:
        """Guarda una nueva receta y devuelve el ID generado."""
        sql = """
            INSERT INTO receta (rut_paciente, nombre_medicamento, principio_activo, dosis, indicaciones, fecha_emision)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                sql,
                (
                    receta.rut_paciente,
                    receta.nombre_medicamento,
                    receta.principio_activo,
                    receta.dosis,
                    receta.indicaciones,
                    receta.fecha_emision
                )
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error al registrar receta en BD: {e}")
            return None
        finally:
            conn.close()

    def obtener_por_paciente(self, rut: str) -> List[Receta]:
        """Obtiene el historial de recetas de un paciente específico."""
        sql = """
            SELECT id_receta, rut_paciente, nombre_medicamento, principio_activo, dosis, indicaciones, fecha_emision
            FROM receta
            WHERE rut_paciente = ?
            ORDER BY id_receta DESC 
        """
        conn = self.db.get_connection()
        recetas = []
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (rut.strip().upper(),))
            for fila in cursor.fetchall():
                recetas.append(Receta(
                    id_receta=fila["id_receta"],
                    rut_paciente=fila["rut_paciente"],
                    nombre_medicamento=fila["nombre_medicamento"],
                    principio_activo=fila["principio_activo"],
                    dosis=fila["dosis"],
                    indicaciones=fila["indicaciones"],
                    fecha_emision=fila["fecha_emision"]
                ))
        except sqlite3.Error as e:
            print(f"Error al consultar recetas: {e}")
        finally:
            conn.close()
        return recetas

    def listar_todas(self) -> List[Receta]:
        """Lista todas las recetas emitidas en la clínica."""
        sql = """
            SELECT id_receta, rut_paciente, nombre_medicamento, principio_activo, dosis, indicaciones, fecha_emision
            FROM receta
            ORDER BY id_receta DESC
        """
        conn = self.db.get_connection()
        recetas = []
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            for fila in cursor.fetchall():
                recetas.append(Receta(
                    id_receta=fila["id_receta"],
                    rut_paciente=fila["rut_paciente"],
                    nombre_medicamento=fila["nombre_medicamento"],
                    principio_activo=fila["principio_activo"],
                    dosis=fila["dosis"],
                    indicaciones=fila["indicaciones"],
                    fecha_emision=fila["fecha_emision"]
                ))
        except sqlite3.Error as e:
            print(f"Error al listar recetas: {e}")
        finally:
            conn.close()
        return recetas