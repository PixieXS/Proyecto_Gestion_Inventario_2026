# Sistema de Gestión de Inventario - v2.0

## Descripción
Sistema completo de gestión de inventario que permite el registro, edición, visualización, eliminación de productos y generación de reportes en PDF.

## Características
- ✅ **CRUD Completo**: Crear, Leer, Actualizar, Eliminar productos
- ✅ **Base de Datos MySQL**: Almacenamiento persistente de datos
- ✅ **Interfaz Gráfica Moderna**: Diseño contemporáneo con Tkinter
- ✅ **Movimientos de Inventario**: Registro detallado de entradas y salidas
- ✅ **Reportes en PDF**: Estadísticas, inventario y movimientos
- ✅ **Estadísticas en Tiempo Real**: Seguimiento de stock y valor
- ✅ **Gráficos Interactivos**: Visualización de datos con Matplotlib (3 tipos)
- ✅ **Análisis de Excel**: Herramienta para visualizar y analizar archivos Excel
- ✅ **Arquitectura Modular**: Código limpio y mantenible

## Estructura Modular del Proyecto

```
Proyecto_STS_Feb_2026/
│
├── main.py                          # Punto de entrada de la aplicación
├── requirements.txt                 # Dependencias Python
├── README.md                        # Documentación
│
├── src/                             # Paquete principal (NUEVO)
│   ├── __init__.py
│   │
│   ├── config/                      # Configuración centralizada
│   │   ├── __init__.py
│   │   └── settings.py              # Constantes, paths y DB config
│   │
│   ├── core/                        # Lógica de base de datos
│   │   ├── __init__.py
│   │   └── database.py              # DatabaseManager (CRUD)
│   │
│   ├── ui/                          # Interfaz gráfica
│   │   ├── __init__.py
│   │   ├── main_window.py           # InventoryManagementApp
│   │   └── styles.py                # Estilos y tema ttk
│   │
│   ├── reports/                     # Generación de reportes
│   │   ├── __init__.py
│   │   └── generator.py             # ReportGenerator (PDF)
│   │
│   └── utils/                       # Utilidades
│       ├── __init__.py
│       └── excel_analyzer.py        # Análisis de Excel
│
├── reportes/                        # Carpeta para PDFs generados
└── __pycache__/                     # Cache Python
```

## Requisitos Previos
- Python 3.7 o superior
- MySQL Server instalado y funcionando
- pip (gestor de paquetes de Python)

## Instalación

### 1. Clonar o descargar el proyecto
```bash
cd Proyecto_Seminario_Software
```

### 2. Crear un entorno virtual (opcional pero recomendado)
```bash
python -m venv venv
# En Windows
venv\Scripts\activate
# En macOS/Linux
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar Base de Datos

Abre el archivo `src/config/settings.py` y actualiza las credenciales MySQL:
```python
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',           # Tu usuario de MySQL
    'password': '12345678',   # Tu contraseña de MySQL
    'database': 'inventory_management',
    'raise_on_warnings': True
}
```

Luego, crea la base de datos en MySQL (opcional - se crea automáticamente):
```bash
mysql -u root -p
```

```sql
CREATE DATABASE inventory_management CHARACTER SET utf8mb4;
EXIT;
```

## Uso

### Ejecutar la aplicación
```bash
python main.py
```

## Funcionalidades

### 1. Gestión de Productos
- **Crear**: Añadir nuevos productos con nombre, descripción, cantidad, precio y proveedor
- **Ver**: Visualizar todos los productos en una tabla
- **Editar**: Doble clic en un producto para cargar sus datos y actualizar
- **Eliminar**: Remover productos del inventario

### 2. Movimientos de Inventario
- Registrar entradas y salidas de producto
- Actualización automática de stock
- Historial de movimientos

### 3. Reportes y Gráficos
- **Reporte de Inventario**: PDF con listado completo de productos
- **Reporte de Movimientos**: PDF con historial de entradas/salidas  
- **Reporte de Estadísticas**: PDF con resumen y métricas
- **Gráficos Interactivos**: 
  - 📦 Stock por Producto (Top 10 productos)
  - 🏭 Distribución por Proveedor (Gráfico de pastel)
  - 📈 Movimientos (últimos 30 días)

### 4. Análisis Excel
- Cargar archivos Excel (.xlsx, .xls)
- Visualizar datos en tabla
- Generar gráficos dinámicos (Línea, Barra, Dispersión, Pastel)

### 5. Estadísticas en Tiempo Real
- Total de productos en inventario
- Stock total en unidades
- Valor total del inventario
- Cantidad de productos con stock bajo

## Base de Datos

### Tabla: productos
```sql
CREATE TABLE productos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    cantidad INT NOT NULL DEFAULT 0,
    precio_unitario DECIMAL(10, 2) NOT NULL,
    proveedor VARCHAR(255),
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
    ultima_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### Tabla: movimientos
```sql
CREATE TABLE movimientos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_producto INT NOT NULL,
    tipo_movimiento VARCHAR(50),
    cantidad INT NOT NULL,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    descripcion TEXT,
    FOREIGN KEY (id_producto) REFERENCES productos(id) ON DELETE CASCADE
);
```

## Troubleshooting

### Error: "No se pudo conectar a la base de datos"
- Verifica que MySQL Server está ejecutándose
- Comprueba las credenciales en `src/config/settings.py`
- Confirma que la base de datos `inventory_management` existe

### Error: "ModuleNotFoundError: No module named 'src'"
- Asegúrate de ejecutar desde la carpeta raíz del proyecto
- Python debe ser ejecutado desde c:\Users\janie\Proyecto_STS_Feb_2026\

### Error: "No module named 'mysql'"
```bash
pip install mysql-connector-python
```

### Los reportes no se generan
- Verifica que existe la carpeta `reportes/` (se crea automáticamente)
- Comprueba permisos de escritura en el directorio del proyecto
- Revisa `src/config/settings.py` - REPORTS_PATH

### La aplicación se cierra al abrir
- Revisa los logs en la consola para mensajes de error
- Verifica que todas las dependencias estén instaladas
- Comprueba la conexión MySQL

## Contribuciones
Las contribuciones son bienvenidas. Para cambios importantes, abre un issue primero.

## Licencia
Este proyecto está bajo licencia MIT.

## Autor
Proyecto Seminario de Software

---
**Última actualización**: Febrero 2026
