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
