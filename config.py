# Configuracion De DB En Mysql
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '',  # Cambiar Con La Contraseña De Mysql De Su Computadora
    'database': 'inventory_management', #Crear Database En Mysql, las tablas 
                                        #se crearan automaticamente al ejecutar el programa
    'raise_on_warnings': False   
}

# Ruta para guardar los reportes
REPORTS_PATH = './reportes/'
