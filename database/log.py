import mysql.connector
from datetime import datetime
from mysql.connector import Error

from config import DB_CONFIG


class LogMixin:

    def registrar_log(self, id_usuario, username, accion, detalle='', producto_afectado=''):
        try:
            self.ping_and_commit()
            self.cursor.execute("""
                INSERT INTO log_actividad
                (id_usuario, username, accion, detalle, producto_afectado)
                VALUES (%s, %s, %s, %s, %s)
            """, (id_usuario, username, accion, detalle, producto_afectado))
            self.connection.commit()
            self._actualizar_backup_auto()
        except Error as e:
            print(f"[WARN] Log: {e}")


    def obtener_log(self, limite=500):
        try:
            self.ping_and_commit()
            self.cursor.execute("""
                SELECT id, username, accion, detalle, producto_afectado, fecha
                FROM log_actividad
                ORDER BY fecha DESC
                LIMIT %s
            """, (limite,))
            return self.cursor.fetchall()
        except Error as e:
            print(e)
            return []

    def backup_base_datos(self, ruta_destino):
        conn = None
        cursor = None
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor(dictionary=True)

            tablas = [
                'roles',
                'permisos',
                'usuarios',
                'proveedores',
                'productos',
                'movimientos',
                'log_actividad',
                'reportes_generados',
            ]
            lines = [
                f"-- Backup generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
                "SET FOREIGN_KEY_CHECKS=0;\n\n",
            ]

            for tabla in tablas:
                cursor.execute(f"SELECT * FROM {tabla}")
                rows = cursor.fetchall()
                if not rows:
                    continue

                cols = list(rows[0].keys())
                cols_str = ', '.join(f"`{c}`" for c in cols)
                lines.append(f"-- Tabla: {tabla}\n")

                for row in rows:
                    vals = []
                    for v in row.values():
                        if v is None:
                            vals.append("NULL")
                        elif isinstance(v, (int, float)):
                            vals.append(str(v))
                        elif isinstance(v, datetime):
                            vals.append(f"'{v.strftime('%Y-%m-%d %H:%M:%S')}'")
                        else:
                            vals.append("'" + str(v).replace("'", "''") + "'")
                    lines.append(
                        f"INSERT IGNORE INTO `{tabla}` ({cols_str}) VALUES ({', '.join(vals)});\n"
                    )
                lines.append("\n")

            lines.append("SET FOREIGN_KEY_CHECKS=1;\n")
            with open(ruta_destino, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return True, ruta_destino
        except Exception as e:
            return False, str(e)
        finally:
            try:
                if cursor:
                    cursor.close()
            except Exception:
                pass
            try:
                if conn and conn.is_connected():
                    conn.close()
            except Exception:
                pass

    def _iterar_sentencias_sql(self, contenido_sql):
        buffer = []
        for line in contenido_sql.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("--"):
                continue
            if stripped.upper().startswith("SET FOREIGN_KEY_CHECKS"):
                continue
            buffer.append(line)
            if stripped.endswith(";"):
                statement = "\n".join(buffer).strip()
                if statement.endswith(";"):
                    statement = statement[:-1].strip()
                if statement:
                    yield statement
                buffer = []

        if buffer:
            statement = "\n".join(buffer).strip()
            if statement:
                yield statement

    def restaurar_base_datos_desde_sql(self, ruta_sql):
        errores = []
        try:
            with open(ruta_sql, "r", encoding="utf-8") as handle:
                contenido = handle.read()

            self.ping_and_commit()
            self.cursor.execute("SET FOREIGN_KEY_CHECKS=0")
            for sentencia in self._iterar_sentencias_sql(contenido):
                try:
                    self.cursor.execute(sentencia)
                except Exception as exc:
                    errores.append(str(exc))
            self.connection.commit()
            return True, errores
        except Exception as exc:
            return False, str(exc)
        finally:
            try:
                self.cursor.execute("SET FOREIGN_KEY_CHECKS=1")
                self.connection.commit()
            except Exception:
                pass
