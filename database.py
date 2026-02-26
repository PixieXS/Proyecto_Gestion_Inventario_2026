import mysql.connector
from mysql.connector import Error
from config import DB_CONFIG
from datetime import datetime

class DatabaseManager:
    """Gestor de conexión y operaciones con la base de datos MySQL"""
    
    def __init__(self):
        self.connection = None
        self.cursor = None
    
    def connect(self):
        """Establecer conexión con la base de datos"""
        try:
            self.connection = mysql.connector.connect(**DB_CONFIG)
            self.cursor = self.connection.cursor(dictionary=True)
            print("[OK] Conexion exitosa a la base de datos")
            return True
        except Error as err:
            print(f"[ERROR] Error de conexion: {err}")
            return False
    
    def disconnect(self):
        """Cerrar la conexión con la base de datos"""
        if self.connection and self.connection.is_connected():
            self.cursor.close()
            self.connection.close()
            print("[OK] Conexion cerrada")
    
    def create_tables(self):
        """Crear las tablas necesarias (o resetearlas si ya existen)"""
        try:
            # Crear tabla de productos
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS productos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(255) NOT NULL,
                    descripcion TEXT,
                    cantidad INT NOT NULL DEFAULT 0,
                    precio_unitario DECIMAL(10, 2) NOT NULL,
                    proveedor VARCHAR(255),
                    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
                    ultima_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            
            # Crear tabla de movimientos
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS movimientos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    id_producto INT NOT NULL,
                    tipo_movimiento VARCHAR(50),
                    cantidad INT NOT NULL,
                    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
                    descripcion TEXT,
                    FOREIGN KEY (id_producto) REFERENCES productos(id) ON DELETE CASCADE
                )
            """)
            
            self.connection.commit()
            print("[OK] Tablas creadas/verificadas exitosamente")
            return True
        except Error as err:
            # Si el error es que las tablas ya existen, no es un problema
            if "already exists" in str(err):
                print("[OK] Las tablas ya existen, usando las existentes")
                return True
            else:
                print(f"[ERROR] Error al crear tablas: {err}")
                return False
    
    # CRUD de Productos
    def crear_producto(self, nombre, descripcion, cantidad, precio_unitario, proveedor):
        """Crear un nuevo producto"""
        try:
            query = """
                INSERT INTO productos 
                (nombre, descripcion, cantidad, precio_unitario, proveedor) 
                VALUES (%s, %s, %s, %s, %s)
            """
            self.cursor.execute(query, (nombre, descripcion, cantidad, precio_unitario, proveedor))
            self.connection.commit()
            return True, "Producto creado exitosamente"
        except Error as err:
            return False, f"Error al crear producto: {err}"
    
    def obtener_productos(self):
        """Obtener todos los productos"""
        try:
            query = "SELECT * FROM productos ORDER BY fecha_registro DESC"
            self.cursor.execute(query)
            return self.cursor.fetchall()
        except Error as err:
            print(f"Error al obtener productos: {err}")
            return []
    
    def obtener_producto(self, id_producto):
        """Obtener un producto por ID"""
        try:
            query = "SELECT * FROM productos WHERE id = %s"
            self.cursor.execute(query, (id_producto,))
            return self.cursor.fetchone()
        except Error as err:
            print(f"Error al obtener producto: {err}")
            return None
    
    def actualizar_producto(self, id_producto, nombre, descripcion, cantidad, precio_unitario, proveedor):
        """Actualizar un producto existente"""
        try:
            query = """
                UPDATE productos 
                SET nombre = %s, descripcion = %s, cantidad = %s, 
                    precio_unitario = %s, proveedor = %s,
                    ultima_actualizacion = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            self.cursor.execute(query, (nombre, descripcion, cantidad, precio_unitario, proveedor, id_producto))
            self.connection.commit()
            return True, "Producto actualizado exitosamente"
        except Error as err:
            return False, f"Error al actualizar producto: {err}"
    
    def eliminar_producto(self, id_producto):
        """Eliminar un producto"""
        try:
            query = "DELETE FROM productos WHERE id = %s"
            self.cursor.execute(query, (id_producto,))
            self.connection.commit()
            return True, "Producto eliminado exitosamente"
        except Error as err:
            return False, f"Error al eliminar producto: {err}"
    
    # Operaciones de Movimientos de Inventario
    def registrar_movimiento(self, id_producto, tipo_movimiento, cantidad, descripcion=""):
        """Registrar movimiento de inventario"""
        try:
            # Registrar movimiento
            query_mov = """
                INSERT INTO movimientos 
                (id_producto, tipo_movimiento, cantidad, descripcion) 
                VALUES (%s, %s, %s, %s)
            """
            self.cursor.execute(query_mov, (id_producto, tipo_movimiento, cantidad, descripcion))
            
            # Actualizar cantidad en productos
            if tipo_movimiento.lower() == "entrada":
                query_prod = "UPDATE productos SET cantidad = cantidad + %s WHERE id = %s"
            else:  # salida
                query_prod = "UPDATE productos SET cantidad = cantidad - %s WHERE id = %s"
            
            self.cursor.execute(query_prod, (cantidad, id_producto))
            self.connection.commit()
            return True, "Movimiento registrado exitosamente"
        except Error as err:
            return False, f"Error al registrar movimiento: {err}"
    
    def obtener_movimientos(self, id_producto=None):
        """Obtener movimientos de inventario"""
        try:
            if id_producto:
                query = "SELECT * FROM movimientos WHERE id_producto = %s ORDER BY fecha DESC"
                self.cursor.execute(query, (id_producto,))
            else:
                query = "SELECT * FROM movimientos ORDER BY fecha DESC"
                self.cursor.execute(query)
            return self.cursor.fetchall()
        except Error as err:
            print(f"Error al obtener movimientos: {err}")
            return []
    
    def obtener_estadisticas(self):
        """Obtener estadísticas del inventario"""
        try:
            stats = {}
            
            # Total de productos
            self.cursor.execute("SELECT COUNT(*) as total FROM productos")
            stats['total_productos'] = self.cursor.fetchone()['total']
            
            # Stock total
            self.cursor.execute("SELECT SUM(cantidad) as total FROM productos")
            result = self.cursor.fetchone()
            stats['stock_total'] = result['total'] if result['total'] else 0
            
            # Valor total del inventario
            self.cursor.execute("SELECT SUM(cantidad * precio_unitario) as valor FROM productos")
            result = self.cursor.fetchone()
            stats['valor_total'] = float(result['valor']) if result['valor'] else 0.0
            
            # Productos con stock bajo (cantidad < 10)
            self.cursor.execute("SELECT COUNT(*) as bajo_stock FROM productos WHERE cantidad < 10")
            stats['bajo_stock'] = self.cursor.fetchone()['bajo_stock']
            
            return stats
        except Error as err:
            print(f"Error al obtener estadísticas: {err}")
            return {}
