from .conexion import Conexion, TODOS_LOS_PERMISOS, PERMISOS_DEFAULT
from .usuarios import UsuariosMixin, _hash
from .productos import ProductosMixin
from .movimientos import MovimientosMixin
from .proveedores import ProveedoresMixin
from .log import LogMixin
from .reportes import ReportesMixin
from .configuracion import ConfiguracionMixin


class DatabaseManager(Conexion, UsuariosMixin, ProductosMixin,
                      MovimientosMixin, ProveedoresMixin, LogMixin,
                      ReportesMixin,
                      ConfiguracionMixin):
    """
    Gestor principal de base de datos.
      - conexion.py       → connect, disconnect, create_tables, categorías seed
      - usuarios.py       → autenticación, CRUD usuarios, roles y permisos
      - productos.py      → CRUD productos, categorías dinámicas, estadísticas
      - movimientos.py    → registrar, buscar, filtrar, importar masivo
      - proveedores.py    → CRUD proveedores
      - log.py            → auditoría y backup
      - reportes.py       → reportes dinámicos, KPIs e historial de reportes
      - configuracion.py  → nombre/logo de empresa, ajustes del sistema
    """
    pass
