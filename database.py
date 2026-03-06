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


    # creacion de tablas en base de datos

    def create_tables(self):
        try:
            # tabla roles
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS roles (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(50) NOT NULL UNIQUE,
                    descripcion TEXT
                )
            """)
            # tabla permisos
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS permisos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    id_rol INT NOT NULL,
                    permiso VARCHAR(100) NOT NULL,
                    FOREIGN KEY (id_rol) REFERENCES roles(id) ON DELETE CASCADE,
                    UNIQUE KEY uq_rol_permiso (id_rol, permiso)
                )
            """)
            # tabla usuarios
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(100) NOT NULL UNIQUE,
                    password_hash VARCHAR(64) NOT NULL,
                    nombre_completo VARCHAR(255),
                    id_rol INT NOT NULL,
                    activo TINYINT DEFAULT 1,
                    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_rol) REFERENCES roles(id)
                )
            """)
            # tabla proveedores
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS proveedores (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(255) NOT NULL,
                    telefono VARCHAR(50),
                    correo VARCHAR(255),
                    direccion TEXT,
                    contacto VARCHAR(255),
                    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # tabla productos
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS productos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(255) NOT NULL,
                    descripcion TEXT,
                    cantidad INT NOT NULL DEFAULT 0,
                    precio_unitario DECIMAL(10,2) NOT NULL,
                    proveedor VARCHAR(255),
                    id_proveedor INT DEFAULT NULL,
                    categoria VARCHAR(100) DEFAULT 'General',
                    stock_minimo INT DEFAULT 5,
                    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
                    ultima_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_proveedor) REFERENCES proveedores(id) ON DELETE SET NULL
                )
            """)
            # tabla movimientos
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS movimientos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    id_producto INT NOT NULL,
                    tipo_movimiento VARCHAR(50),
                    cantidad INT NOT NULL,
                    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
                    descripcion TEXT,
                    id_usuario INT DEFAULT NULL,
                    FOREIGN KEY (id_producto) REFERENCES productos(id) ON DELETE CASCADE,
                    FOREIGN KEY (id_usuario) REFERENCES usuarios(id) ON DELETE SET NULL
                )
            """)
            # tabla de log de actividad
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS log_actividad (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    id_usuario INT DEFAULT NULL,
                    username VARCHAR(100),
                    accion VARCHAR(255) NOT NULL,
                    detalle TEXT,
                    producto_afectado VARCHAR(255),
                    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_usuario) REFERENCES usuarios(id) ON DELETE SET NULL
                )
            """)
            self.connection.commit()

            # migrar para base creada
            self._migrar_columnas()

            # datos iniciales
            self._seed_inicial()
            return True
        except Error as e:
            if e.errno == 1050 or "already exists" in str(e):
                print("[OK] Tablas ya existen, usando las existentes")
                try:
                    self._migrar_columnas()
                    self._seed_inicial()
                except Exception:
                    pass
                return True
            print(f"[ERROR] Creando tablas: {e}")
            return False
        #aqui agregamos las columnas a las tablas
    def _migrar_columnas(self):
        """Agregar columnas nuevas a tablas existentes si no existen."""
        migraciones = [
            ("productos", "stock_minimo",  "ALTER TABLE productos ADD COLUMN stock_minimo INT DEFAULT 5"),
            ("productos", "id_proveedor",  "ALTER TABLE productos ADD COLUMN id_proveedor INT DEFAULT NULL"),
            ("productos", "categoria",     "ALTER TABLE productos ADD COLUMN categoria VARCHAR(100) DEFAULT 'General'"),
            ("movimientos", "id_usuario",  "ALTER TABLE movimientos ADD COLUMN id_usuario INT DEFAULT NULL"),
        ]
        for tabla, columna, sql in migraciones:
            try:
                self.cursor.execute(f"SELECT {columna} FROM {tabla} LIMIT 1")
                self.cursor.fetchall()
            except Error:
                try:
                    self.cursor.execute(sql)
                    self.connection.commit()
                    print(f"[OK] Migración: {tabla}.{columna}")
                except Error as e:
                    print(f"[WARN] Migración {columna}: {e}")

    def _seed_inicial(self):
        """Insertar roles, permisos y usuario admin si la BD está vacía."""
        self.cursor.execute("SELECT COUNT(*) AS n FROM roles")
        if self.cursor.fetchone()['n'] > 0:
            return

        # roles
        for nombre, desc in [
            ('Administrador', 'Acceso total al sistema'),
            ('Gerente',       'Reportes y análisis'),
            ('Empleado',      'Registrar movimientos'),
        ]:
            self.cursor.execute(
                "INSERT INTO roles (nombre, descripcion) VALUES (%s, %s)", (nombre, desc))
        self.connection.commit()

        # permisos para los roles
        for rol_nombre, lista in PERMISOS_DEFAULT.items():
            self.cursor.execute("SELECT id FROM roles WHERE nombre=%s", (rol_nombre,))
            row = self.cursor.fetchone()
            if not row:
                continue
            id_rol = row['id']
            for p in lista:
                try:
                    self.cursor.execute(
                        "INSERT IGNORE INTO permisos (id_rol, permiso) VALUES (%s,%s)", (id_rol, p))
                except Error:
                    pass
        self.connection.commit()

        # usuarios creados por defecto
        self.cursor.execute("SELECT id FROM roles WHERE nombre='Administrador'")
        id_admin = self.cursor.fetchone()['id']
        self.cursor.execute("SELECT id FROM roles WHERE nombre='Gerente'")
        id_gerente = self.cursor.fetchone()['id']
        self.cursor.execute("SELECT id FROM roles WHERE nombre='Empleado'")
        id_empleado = self.cursor.fetchone()['id']

        for usr, pwd, rid, nombre in [
            ('admin',    'admin123',    id_admin,    'Administrador'),
            ('gerente',  'gerente123',  id_gerente,  'Gerente'),
            ('empleado', 'empleado123', id_empleado, 'Empleado'),
        ]:
            try:
                self.cursor.execute("""
                    INSERT IGNORE INTO usuarios (username, password_hash, nombre_completo, id_rol)
                    VALUES (%s, %s, %s, %s)
                """, (usr, _hash(pwd), nombre, rid))
            except Error:
                pass
        self.connection.commit()
        print("[OK] Datos iniciales creados (admin/admin123)")

          # autenticacion de usuarios

    def autenticar_usuario(self, username, password):
        """Retorna dict con info del usuario o None si falla."""
        try:
            self.cursor.execute("""
                SELECT u.id, u.username, u.nombre_completo, u.activo,
                       r.id AS id_rol, r.nombre AS rol
                FROM usuarios u
                JOIN roles r ON u.id_rol = r.id
                WHERE u.username = %s AND u.password_hash = %s
            """, (username, _hash(password)))
            usuario = self.cursor.fetchone()
            if not usuario:
                return None, "Usuario o contraseña incorrectos"
            if not usuario['activo']:
                return None, "Usuario desactivado. Contacte al administrador."

            # permisos de los usuarios
            self.cursor.execute(
                "SELECT permiso FROM permisos WHERE id_rol = %s", (usuario['id_rol'],))
            permisos = [r['permiso'] for r in self.cursor.fetchall()]
            usuario['permisos'] = permisos
            return usuario, None
        except Error as e:
            return None, str(e)

    def tiene_permiso(self, usuario, permiso):
        permisos = usuario.get('permisos', [])
        return 'all' in permisos or permiso in permisos

    # gestionamos usuarios

    def obtener_usuarios(self):
        try:
            self.cursor.execute("""
                SELECT u.id, u.username, u.nombre_completo, u.activo,
                       r.nombre AS rol, u.fecha_creacion
                FROM usuarios u JOIN roles r ON u.id_rol = r.id
                ORDER BY u.id
            """)
            return self.cursor.fetchall()
        except Error as e:
            print(e); return []

    def crear_usuario(self, username, password, nombre_completo, id_rol):
        try:
            self.cursor.execute("""
                INSERT INTO usuarios (username, password_hash, nombre_completo, id_rol)
                VALUES (%s, %s, %s, %s)
            """, (username, _hash(password), nombre_completo, id_rol))
            self.connection.commit()
            return True, "Usuario creado"
        except Error as e:
            return False, str(e)

    def actualizar_usuario(self, id_usuario, nombre_completo, id_rol, activo):
        try:
            self.cursor.execute("""
                UPDATE usuarios SET nombre_completo=%s, id_rol=%s, activo=%s WHERE id=%s
            """, (nombre_completo, id_rol, activo, id_usuario))
            self.connection.commit()
            return True, "Usuario actualizado"
        except Error as e:
            return False, str(e)

    def cambiar_password(self, id_usuario, password_actual, password_nueva):
        try:
            self.cursor.execute(
                "SELECT id FROM usuarios WHERE id=%s AND password_hash=%s",
                (id_usuario, _hash(password_actual)))
            if not self.cursor.fetchone():
                return False, "Contraseña actual incorrecta"
            self.cursor.execute(
                "UPDATE usuarios SET password_hash=%s WHERE id=%s",
                (_hash(password_nueva), id_usuario))
            self.connection.commit()
            return True, "Contraseña actualizada"
        except Error as e:
            return False, str(e)

    def eliminar_usuario(self, id_usuario):
        try:
            self.cursor.execute("DELETE FROM usuarios WHERE id=%s", (id_usuario,))
            self.connection.commit()
            return True, "Usuario eliminado"
        except Error as e:
            return False, str(e)
        
 # ── gestion de roles y permisos

    def obtener_roles(self):
        try:
            self.cursor.execute("SELECT * FROM roles ORDER BY id")
            return self.cursor.fetchall()
        except Error as e:
            print(e); return []

    def obtener_permisos_rol(self, id_rol):
        try:
            self.cursor.execute("SELECT permiso FROM permisos WHERE id_rol=%s", (id_rol,))
            return [r['permiso'] for r in self.cursor.fetchall()]
        except Error as e:
            print(e); return []

    def actualizar_permisos_rol(self, id_rol, lista_permisos):
        try:
            self.cursor.execute("DELETE FROM permisos WHERE id_rol=%s", (id_rol,))
            for p in lista_permisos:
                self.cursor.execute(
                    "INSERT IGNORE INTO permisos (id_rol, permiso) VALUES (%s,%s)", (id_rol, p))
            self.connection.commit()
            return True, "Permisos actualizados"
        except Error as e:
            return False, str(e)

    # obtener provedores

    def obtener_proveedores(self):
        try:
            self.ping_and_commit()
            self.cursor.execute("SELECT * FROM proveedores ORDER BY nombre")
            return self.cursor.fetchall()
        except Error as e:
            print(e); return []

    def crear_proveedor(self, nombre, telefono, correo, direccion, contacto=''):
        try:
            self.cursor.execute("""
                INSERT INTO proveedores (nombre, telefono, correo, direccion, contacto)
                VALUES (%s,%s,%s,%s,%s)
            """, (nombre, telefono, correo, direccion, contacto))
            self.connection.commit()
            return True, "Proveedor creado"
        except Error as e:
            return False, str(e)

    def actualizar_proveedor(self, id_prov, nombre, telefono, correo, direccion, contacto=''):
        try:
            self.cursor.execute("""
                UPDATE proveedores SET nombre=%s,telefono=%s,correo=%s,direccion=%s,contacto=%s
                WHERE id=%s
            """, (nombre, telefono, correo, direccion, contacto, id_prov))
            self.connection.commit()
            return True, "Proveedor actualizado"
        except Error as e:
            return False, str(e)

    def eliminar_proveedor(self, id_prov):
        try:
            self.cursor.execute("DELETE FROM proveedores WHERE id=%s", (id_prov,))
            self.connection.commit()
            return True, "Proveedor eliminado"
        except Error as e:
            return False, str(e)

    def obtener_productos_proveedor(self, id_prov):
        try:
            self.cursor.execute(
                "SELECT id,nombre FROM productos WHERE id_proveedor=%s", (id_prov,))
            return self.cursor.fetchall()
        except Error as e:
            print(e); return []