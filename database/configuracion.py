from mysql.connector import Error


class ConfiguracionMixin:
    def get_config(self, clave, default=''):
        try:
            self.cursor.execute(
                "SELECT valor FROM configuracion_sistema WHERE clave=%s", (clave,))
            row = self.cursor.fetchone()
            return row['valor'] if row else default
        except Error:
            return default

    def set_config(self, clave, valor):
        try:
            self.cursor.execute("""
                INSERT INTO configuracion_sistema (clave, valor)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE valor=%s
            """, (clave, valor, valor))
            self.connection.commit()
            return True
        except Error as e:
            return False

    def get_empresa_nombre(self):
        return self.get_config('empresa_nombre', 'Mi Empresa')

    def get_empresa_logo(self):
        return self.get_config('empresa_logo', '')

    def set_empresa_nombre(self, nombre):
        return self.set_config('empresa_nombre', nombre.strip())

    def set_empresa_logo(self, ruta):
        return self.set_config('empresa_logo', ruta.strip())

    def get_empresa_direccion(self):
        return self.get_config('empresa_direccion', '')

    def get_empresa_telefono(self):
        return self.get_config('empresa_telefono', '')

    def set_empresa_direccion(self, val):
        return self.set_config('empresa_direccion', val.strip())

    def set_empresa_telefono(self, val):
        return self.set_config('empresa_telefono', val.strip())
