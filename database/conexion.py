import mysql.connector
from mysql.connector import Error
from config import DB_CONFIG

TODOS_LOS_PERMISOS = [
    'ver_reportes', 'exportar_inventario', 'exportar_movimientos', 'exportar_todo',
    'backup_bd', 'gestionar_usuarios', 'gestionar_roles', 'ver_auditoria',
    'configuracion', 'registrar_movimientos', 'crear_producto', 'editar_producto',
    'inhabilitar_producto', 'cambiar_password', 'ver_graficos', 'reporte_fechas',
    'ver_proveedores', 'gestionar_proveedores', 'ver_historial_producto', 'analizar_excel',
]

PERMISOS_DEFAULT = {
    'Administrador': ['all'],
    'Gerente': [
        'ver_reportes', 'ver_graficos', 'reporte_fechas',
        'exportar_inventario', 'exportar_movimientos', 'exportar_todo',
        'ver_proveedores', 'cambiar_password', 'ver_historial_producto', 'analizar_excel',
    ],
    'Empleado': ['registrar_movimientos', 'cambiar_password', 'ver_historial_producto'],
}


class Conexion:
    def __init__(self):
        self.connection = None
        self.cursor = None

    def connect(self):
        try:
            nombre_bd = DB_CONFIG['database']

            # Conectar directamente con la base de datos configurada
            self.connection = mysql.connector.connect(**DB_CONFIG)
            self.cursor = self.connection.cursor(dictionary=True)
            print(f"[OK] Conexión exitosa — base de datos: {nombre_bd}")
            return True
        except Error as e:
            print(f"[ERROR] Conexión: {e}")
            return False

    def disconnect(self):
        if self.connection and self.connection.is_connected():
            self.cursor.close()
            self.connection.close()

    def ping_and_commit(self):
        try:
            if not self.connection or not self.connection.is_connected():
                self.connection.reconnect(attempts=3, delay=1)
                self.cursor = self.connection.cursor(dictionary=True)
                return
            self.connection.commit()
        except Exception as e:
            print(f"[WARN] ping_and_commit: {e}")
            try:
                self.connect()
            except Exception:
                pass

    def create_tables(self):
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS roles (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(50) NOT NULL UNIQUE,
                    descripcion TEXT
                )""")
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS permisos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    id_rol INT NOT NULL,
                    permiso VARCHAR(100) NOT NULL,
                    FOREIGN KEY (id_rol) REFERENCES roles(id) ON DELETE CASCADE,
                    UNIQUE KEY uq_rol_permiso (id_rol, permiso)
                )""")
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(100) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    nombre_completo VARCHAR(255),
                    id_rol INT NOT NULL,
                    activo TINYINT DEFAULT 1,
                    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_rol) REFERENCES roles(id)
                )""")
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS categorias (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(100) NOT NULL UNIQUE,
                    descripcion TEXT,
                    activa TINYINT DEFAULT 1,
                    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP
                )""")
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS proveedores (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(255) NOT NULL,
                    telefono VARCHAR(50),
                    correo VARCHAR(255),
                    direccion TEXT,
                    contacto VARCHAR(255),
                    activo TINYINT DEFAULT 1,
                    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP
                )""")
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS productos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(255) NOT NULL,
                    codigo VARCHAR(100) DEFAULT NULL UNIQUE,
                    descripcion TEXT,
                    cantidad INT NOT NULL DEFAULT 0,
                    precio_unitario DECIMAL(10,2) NOT NULL,
                    proveedor VARCHAR(255),
                    id_proveedor INT DEFAULT NULL,
                    categoria VARCHAR(100) DEFAULT 'General',
                    stock_minimo INT DEFAULT 5,
                    activo TINYINT DEFAULT 1,
                    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
                    ultima_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_proveedor) REFERENCES proveedores(id) ON DELETE SET NULL
                )""")
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
                )""")
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS historial_precios (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    id_producto INT NOT NULL,
                    precio_anterior DECIMAL(10,2) NOT NULL,
                    precio_nuevo DECIMAL(10,2) NOT NULL,
                    id_usuario INT DEFAULT NULL,
                    username VARCHAR(100),
                    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_producto) REFERENCES productos(id) ON DELETE CASCADE,
                    FOREIGN KEY (id_usuario) REFERENCES usuarios(id) ON DELETE SET NULL
                )""")
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
                )""")
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS reportes_generados (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    tipo_reporte VARCHAR(100) NOT NULL,
                    titulo_reporte VARCHAR(255),
                    id_usuario INT DEFAULT NULL,
                    username VARCHAR(100),
                    filtros_json LONGTEXT,
                    formato VARCHAR(50) DEFAULT 'Vista previa',
                    total_registros INT DEFAULT 0,
                    fecha_generacion DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_usuario) REFERENCES usuarios(id) ON DELETE SET NULL
                )""")
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS configuracion_sistema (
                    clave VARCHAR(100) PRIMARY KEY,
                    valor TEXT
                )""")
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS intentos_login (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(100) NOT NULL,
                    ip VARCHAR(50),
                    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
                    exitoso TINYINT DEFAULT 0,
                    INDEX idx_user_fecha (username, fecha)
                )""")
            self.connection.commit()
            self._migrar_columnas()
            self._ajustar_hash_password()
            self._seed_inicial()
            return True
        except Error as e:
            if e.errno == 1050 or "already exists" in str(e):
                try:
                    self._migrar_columnas()
                    self._ajustar_hash_password()
                    self._seed_inicial()
                except Exception:
                    pass
                return True
            print(f"[ERROR] Creando tablas: {e}")
            return False

    def _migrar_columnas(self):
        migraciones = [
            ("productos",   "stock_minimo", "ALTER TABLE productos ADD COLUMN stock_minimo INT DEFAULT 5"),
            ("productos",   "id_proveedor", "ALTER TABLE productos ADD COLUMN id_proveedor INT DEFAULT NULL"),
            ("productos",   "categoria",    "ALTER TABLE productos ADD COLUMN categoria VARCHAR(100) DEFAULT 'General'"),
            ("productos",   "activo",       "ALTER TABLE productos ADD COLUMN activo TINYINT DEFAULT 1"),
            ("movimientos", "id_usuario",   "ALTER TABLE movimientos ADD COLUMN id_usuario INT DEFAULT NULL"),
            ("categorias",  "activa",       "ALTER TABLE categorias ADD COLUMN activa TINYINT DEFAULT 1"),
            ("proveedores", "activo",       "ALTER TABLE proveedores ADD COLUMN activo TINYINT DEFAULT 1"),
            ("productos",   "codigo",       "ALTER TABLE productos ADD COLUMN codigo VARCHAR(100) DEFAULT NULL"),
            ("productos",   "imagen_path",  "ALTER TABLE productos ADD COLUMN imagen_path VARCHAR(500) DEFAULT NULL"),
            ("productos",   "unidad_medida","ALTER TABLE productos ADD COLUMN unidad_medida VARCHAR(50) DEFAULT 'Unidad'"),
            ("productos",   "stock_maximo", "ALTER TABLE productos ADD COLUMN stock_maximo INT DEFAULT NULL"),
            ("productos",   "precio_compra","ALTER TABLE productos ADD COLUMN precio_compra DECIMAL(10,2) DEFAULT NULL"),
            ("proveedores", "ruc_nit",      "ALTER TABLE proveedores ADD COLUMN ruc_nit VARCHAR(50) DEFAULT NULL"),
            ("usuarios",    "ultimo_login", "ALTER TABLE usuarios ADD COLUMN ultimo_login DATETIME DEFAULT NULL"),
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

    def _ajustar_hash_password(self):
        try:
            self.cursor.execute(
                "ALTER TABLE usuarios MODIFY COLUMN password_hash VARCHAR(255) NOT NULL")
            self.connection.commit()
        except Error as e:
            print(f"[WARN] Migración password_hash: {e}")