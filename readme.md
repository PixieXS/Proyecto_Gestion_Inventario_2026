# 📦 Sistema de Gestión de Inventario

Sistema de escritorio para la gestión de inventario de productos, desarrollado en Python con interfaz gráfica Tkinter y base de datos MySQL.

---

## 🚀 Características principales

- 🔐 Autenticación con sistema de roles y permisos (Administrador, Gerente, Empleado)
- 📦 CRUD completo de productos con categorías y stock mínimo configurable
- 🚨 Alertas automáticas de stock crítico con colores de alerta en la tabla
- 🏭 Módulo completo de proveedores con productos asociados
- ➡️ Registro de movimientos de inventario (entradas y salidas)
- 📋 Historial de movimientos por producto con usuario responsable
- 🧾 Registro de auditoría de todas las acciones del sistema
- 📊 Reportes en PDF (inventario, movimientos, estadísticas, rango de fechas)
- 📥 Exportación a Excel con ajuste automático de columnas
- 📈 Visualización de gráficos estadísticos (4 pestañas)
- 🔬 Analizador de archivos Excel externos con gráficas personalizadas
- 💾 Backup de la base de datos en formato SQL
- 👥 Gestión de usuarios y configuración de permisos por rol
- 📘 Manual de usuario integrado en PDF (17 secciones)

---

## 🛠️ Tecnologías utilizadas

| Tecnología | Uso |
|---|---|
| Python 3 | Lenguaje principal |
| Tkinter | Interfaz gráfica de escritorio |
| MySQL | Base de datos relacional |
| mysql-connector-python | Conexión a MySQL |
| ReportLab | Generación de reportes PDF |
| OpenPyXL | Exportación a Excel |
| Matplotlib | Visualización de gráficos |
| Pandas | Análisis de archivos Excel |
| Hashlib (SHA-256) | Cifrado de contraseñas |

---

## 📋 Requisitos previos

- Python 3.10 o superior
- MySQL 8.0 o superior (puede usarse con XAMPP o Laragon)
- pip

---

## ⚙️ Instalación

**1. Clonar el repositorio**
```bash
git clone https://github.com/PixieXS/Proyecto_Gestion_Inventario_2026/
cd Proyecto_Gestion_Inventario_2026
```

**2. Instalar dependencias**
```bash
pip install mysql-connector-python reportlab openpyxl matplotlib pandas
```

**3. Configurar la base de datos**

Asegurarse de que MySQL esté corriendo, luego editar `config.py` con los datos de conexión:
```python
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '',        # tu contraseña de MySQL
    'database': 'inventory_management',
    'raise_on_warnings': False
}
```

> La base de datos y todas las tablas se crean automáticamente al ejecutar el programa por primera vez.

**4. Ejecutar el programa**
```bash
py main.py
```

---

## 👤 Usuarios por defecto

| Usuario | Contraseña | Rol |
|---|---|---|
| `admin` | `admin123` | Administrador |
| `gerente` | `gerente123` | Gerente |
| `empleado` | `empleado123` | Empleado |

> ⚠️ Se recomienda cambiar las contraseñas por defecto en el primer uso desde **Menú → Mi Cuenta → Cambiar Contraseña**.

---

## 🗂️ Estructura del proyecto

```
proyecto_v2/
├── main.py                  # Punto de entrada, inicializa DB y login
├── gui.py                   # Interfaz gráfica principal
├── database.py              # Lógica de base de datos y consultas
├── config.py                # Configuración de conexión MySQL
├── reports.py               # Generación de reportes PDF
├── export_excel.py          # Exportación a Excel
├── excel_analysis.py        # Analizador de archivos Excel
├── users_module.py          # Gestión de usuarios y roles
├── suppliers_module.py      # Módulo de proveedores
├── activity_log_module.py   # Visor de auditoría
├── manual_usuario.pdf       # Manual de usuario integrado
├── check_mysql.py           # Verificador de conexión MySQL
├── app_icon.ico             # Ícono de la aplicación
└── reportes/                # Carpeta donde se guardan los PDFs generados
```

---

## 🔐 Roles y permisos

| Permiso | Administrador | Gerente | Empleado |
|---|:---:|:---:|:---:|
| Crear/editar/eliminar productos | ✅ | ✅ | ❌ |
| Registrar movimientos | ✅ | ✅ | ✅ |
| Ver reportes y gráficos | ✅ | ✅ | ❌ |
| Exportar inventario a Excel | ✅ | ✅ | ❌ |
| Gestionar proveedores | ✅ | ✅ | ❌ |
| Gestionar usuarios y roles | ✅ | ❌ | ❌ |
| Ver auditoría | ✅ | ❌ | ❌ |
| Backup de base de datos | ✅ | ❌ | ❌ |
| Cambiar contraseña propia | ✅ | ✅ | ✅ |

> Los permisos de Gerente y Empleado son configurables desde **Menú → Administración → Gestionar Roles**.

---

## 👨‍💻 Equipo de desarrollo

| Nombre | Rama |
|---|---|
| Carlos Sagastume | `carlos-sagastume` |
| Aaron Gomez | `aaron-gomez` |
| Ashly Guillen | `ashly-guillen` |
| Jose Castro | `jose-castro` |
| Melvin Velasquez | `melvin-velasquez` |

---

## 🏫 Información académica

- **Universidad:** Universidad Catolica De Honduras (UNICAH)
- **Carrera:** Ingeniería en Sistemas
- **Curso:** Seminario Taller De Software
- **Año:** 2026

---

## 📄 Licencia

Proyecto Académico — Universidad Catolica De Honduras (UNICAH) 2026.
