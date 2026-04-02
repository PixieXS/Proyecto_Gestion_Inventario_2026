import json, os

_BASE = os.path.dirname(os.path.abspath(__file__))
_CFG_FILE = os.path.join(_BASE, 'db_config.json')

# Defaults — se sobreescriben si existe db_config.json
DB_CONFIG = {
    'host':     'localhost',
    'port':     3306,
    'user':     'root',
    'password': '',
    'database': 'inventario_sts',
    'charset':  'utf8mb4',
}

# Cargar configuración guardada si existe
if os.path.exists(_CFG_FILE):
    try:
        with open(_CFG_FILE, 'r') as f:
            _saved = json.load(f)
            DB_CONFIG['host']     = _saved.get('host',     DB_CONFIG['host'])
            DB_CONFIG['port']     = int(_saved.get('port', DB_CONFIG['port']))
            DB_CONFIG['user']     = _saved.get('user',     DB_CONFIG['user'])
            DB_CONFIG['password'] = _saved.get('password', DB_CONFIG['password'])
            DB_CONFIG['database'] = _saved.get('database', DB_CONFIG['database'])
    except Exception:
        pass

# Ruta para guardar reportes
REPORTS_PATH = './reportes/'