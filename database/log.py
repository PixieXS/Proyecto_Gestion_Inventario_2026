import mysql.connector
from datetime import datetime
from mysql.connector import Error

from config import DB_CONFIG


class LogMixin:

    def registrar_log(self, id_usuario, username, accion, detalle='', producto_afectado=''):
        try:
            self.ping_and_commit()
            self.cursor.execute("""
                INSERT INTO log_actividad
                (id_usuario, username, accion, detalle, producto_afectado)
                VALUES (%s, %s, %s, %s, %s)
            """, (id_usuario, username, accion, detalle, producto_afectado))
            self.connection.commit()
            self._actualizar_backup_auto()
        except Error as e:
            print(f"[WARN] Log: {e}")


    def obtener_log(self, limite=500):
        try:
            self.ping_and_commit()
            self.cursor.execute("""
                SELECT id, username, accion, detalle, producto_afectado, fecha
                FROM log_actividad
                ORDER BY fecha DESC
                LIMIT %s
            """, (limite,))
            return self.cursor.fetchall()
        except Error as e:
            print(e)
            return []

    
