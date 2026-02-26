import sys
import traceback
print('EXE:', sys.executable)
try:
    import mysql.connector
    print('mysql.connector importado correctamente')
except Exception:
    print('Error al importar mysql.connector:')
    traceback.print_exc()
