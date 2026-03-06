import mysql.connector
from mysql.connector import Error
from config import DB_CONFIG
from datetime import datetime
import hashlib
import os


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

# Permisos Disponibles
TODOS_LOS_PERMISOS = [
    'ver_reportes',
    'exportar_inventario',
    'exportar_movimientos',
    'exportar_todo',
    'backup_bd',
    'gestionar_usuarios',
    'gestionar_roles',
    'ver_auditoria',
    'configuracion',
    'registrar_movimientos',
    'crear_producto',
    'editar_producto',
    'eliminar_producto',
    'cambiar_password',
    'ver_graficos',
    'reporte_fechas',
    'ver_proveedores',
    'gestionar_proveedores',
    'ver_historial_producto',
    'analizar_excel',
]

PERMISOS_DEFAULT = {
    'Administrador': ['all'],
    'Gerente': [
        'ver_reportes', 'exportar_inventario', 'ver_graficos', 'reporte_fechas',
        'ver_proveedores', 'cambiar_password', 'ver_historial_producto', 'analizar_excel',
    ],
    'Empleado': [
        'registrar_movimientos', 'cambiar_password', 'ver_historial_producto',
    ],
}

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.cursor = None

    #conexion a base de datos

    def connect(self):
        try:
            self.connection = mysql.connector.connect(**DB_CONFIG)
            self.cursor = self.connection.cursor(dictionary=True)
            print("[OK] Conexión exitosa")
            return True
        except Error as e:
            print(f"[ERROR] Conexión: {e}")
            return False

    def disconnect(self):
        if self.connection and self.connection.is_connected():
            self.cursor.close()
            self.connection.close()

    def ping_and_commit(self):
        """Cierra la transacción implícita abierta y reconecta si es necesario.
        
        MySQL Connector opera con autocommit=False por defecto.
        Cuando otro cliente (ej. Workbench) inserta datos y los commitea,
        esta conexión no los ve hasta que se cierre su transacción activa.
        Hacer commit() antes de leer fuerza a MySQL a dar una vista fresca.
        """
        try:
            # reconectar si se cae la conexcion
            if not self.connection or not self.connection.is_connected():
                self.connection.reconnect(attempts=3, delay=1)
                self.cursor = self.connection.cursor(dictionary=True)
                return
            # aqui cerramos para no ver la sesion de otro usuario
            self.connection.commit()
        except Exception as e:
            print(f"[WARN] ping_and_commit: {e}")
            try:
                self.connect()
            except Exception:
                pass