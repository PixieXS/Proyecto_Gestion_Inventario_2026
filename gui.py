import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from database import DatabaseManager
from reports import ReportGenerator
from export_excel import ExcelExporter
from datetime import datetime, timedelta

import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from excel_analysis import ExcelAnalyzer

class InventoryManagementApp:
    """Aplicación de gestión de inventario con interfaz Tkinter"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Gestión de Inventario")
        self.root.geometry("1400x800")
        self.root.resizable(True, True)
        
        
        self.color_primary = "#2563EB"      
        self.color_secondary = "#10B981"    
        self.color_danger = "#EF4444"       
        self.color_warning = "#F59E0B"      
        self.color_bg = "#F8FAFC"
        self.color_sc = "#1C1D1D"           
        self.color_surface = "#FFFFFF"      
        self.color_text = "#1E293B"         
        self.color_text_muted = "#64748B"   
        self.color_border = "#E2E8F0"       
        
        # Configurar tema de la aplicación
        self.root.config(bg=self.color_bg)
        self._configurar_estilos()
        
        # Inicializar base de datos
        self.db = DatabaseManager()
        self.report_gen = ReportGenerator()
        self.excel_exporter = ExcelExporter()
        self.gen_reportes = ReportGenerator()
        
        if not self.db.connect():
            messagebox.showerror("Error", "No se pudo conectar a la base de datos")
            return
        
        if not self.db.create_tables():
            messagebox.showerror("Error", "No se pudieron crear las tablas")
            return
        
        # Variables de sesión
        self.producto_seleccionado = None
        
        # Crear interfaz
        self.crear_interfaz()
        self.cargar_productos()
    
    
    def _configurar_estilos(self):
        """Configurar estilos modernos para todos los widgets"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configurar colores generales
        style.configure('TFrame', background=self.color_bg)
        style.configure('TLabel', background=self.color_bg, foreground=self.color_text, 
                       font=('Segoe UI', 9))
        style.configure('TLabelframe', background=self.color_bg, foreground=self.color_text,
                       font=('Segoe UI', 9, 'bold'), padding=2)
        style.configure('TLabelframe.Label', background=self.color_bg, foreground=self.color_text)
        style.configure('TEntry', fieldbackground=self.color_surface, foreground=self.color_text,
                       font=('Segoe UI', 9))
        style.map('TEntry', fieldbackground=[('focus', '#E0EDFF')])
        
        # Estilo para header
        style.configure('Header.TLabel', background=self.color_bg, foreground=self.color_primary,
                       font=('Segoe UI', 16, 'bold'))
        
        # Estilo para Label
        style.configure('TLabel', background=self.color_bg, foreground=self.color_text)
        
        # Estilo para Stats
        style.configure('Stats.TLabel', background=self.color_bg, foreground=self.color_text,
                       font=('Segoe UI', 10))
        
        # Botón de Crear (Verde)
        style.configure('Create.TButton', font=('Segoe UI', 9, 'bold'), padding=8)
        style.map('Create.TButton',
                 background=[('!active', self.color_secondary), ('active', '#059669')],
                 foreground=[('!active', self.color_surface), ('active', self.color_surface)])
        
        # Botón de Actualizar (Azul)
        style.configure('Update.TButton', font=('Segoe UI', 9, 'bold'), padding=8)
        style.map('Update.TButton',
                 background=[('!active', self.color_primary), ('active', '#1D4ED8')],
                 foreground=[('!active', self.color_surface), ('active', self.color_surface)])
        
        # Botón de Eliminar (Rojo)
        style.configure('Delete.TButton', font=('Segoe UI', 9, 'bold'), padding=8)
        style.map('Delete.TButton',
                 background=[('!active', self.color_danger), ('active', '#DC2626')],
                 foreground=[('!active', self.color_surface), ('active', self.color_surface)])
        
        # Botón estándar
        style.configure('TButton', font=('Segoe UI', 9, 'bold'), padding=8)
        style.map('TButton',
                 background=[('!active', self.color_primary), ('active', '#1D4ED8')],
                 foreground=[('!active', self.color_surface), ('active', self.color_surface)])
        
        # Combobox 
        style.configure('TCombobox', fieldbackground=self.color_surface, foreground=self.color_text,
                       font=('Segoe UI', 9))
        style.map('TCombobox', fieldbackground=[('focus', '#E0EDFF')])
        
        # Treeview
        style.configure('Treeview', background=self.color_surface, foreground=self.color_text,
                       fieldbackground=self.color_surface, borderwidth=1, font=('Segoe UI', 9))
        style.configure('Treeview.Heading', background=self.color_primary, foreground=self.color_surface,
                       font=('Segoe UI', 9, 'bold'), relief='flat')
        style.map('Treeview.Heading', background=[('active', '#1D4ED8')])
        style.map('Treeview', background=[('selected', '#E0EDFF')], foreground=[('selected', self.color_primary)])
        
        # Scrollbar
        style.configure('TScrollbar', background=self.color_sc, troughcolor=self.color_border)
    

    def crear_interfaz(self):
        """Crear la interfaz principal mejorada"""
        # Menú
        menubar = tk.Menu(self.root, bg=self.color_surface, fg=self.color_text,
                         activebackground=self.color_primary, activeforeground=self.color_surface,
                         font=('Segoe UI', 9))
        self.root.config(menu=menubar)
        
        archivo_menu = tk.Menu(menubar, bg=self.color_surface, fg=self.color_text,
                              activebackground=self.color_primary, activeforeground=self.color_surface,
                              tearoff=0, font=('Segoe UI', 9))
        menubar.add_cascade(label="📁 Archivo", menu=archivo_menu)
        archivo_menu.add_command(label="Salir", command=self.root.quit)
        
        reportes_menu = tk.Menu(menubar, bg=self.color_surface, fg=self.color_text,
                               activebackground=self.color_primary, activeforeground=self.color_surface,
                               tearoff=0, font=('Segoe UI', 9))
        menubar.add_cascade(label="📊 Reportes", menu=reportes_menu)
        reportes_menu.add_command(label="Inventario", command=self.generar_reporte_inventario)
        reportes_menu.add_command(label="Movimientos", command=self.generar_reporte_movimientos)
        reportes_menu.add_command(label="Estadísticas", command=self.generar_reporte_estadisticas)
        reportes_menu.add_separator()
        reportes_menu.add_command(label="📥 Exportar Inventario (Excel)", command=self.exportar_inventario_excel)
        reportes_menu.add_command(label="📥 Exportar Movimientos (Excel)", command=self.exportar_movimientos_excel)
        reportes_menu.add_command(label="📥 Exportar Todo (Excel)", command=self.exportar_completo_excel)
        reportes_menu.add_separator()
        reportes_menu.add_command(label="Ver Gráficos", command=self.abrir_ventana_graficos)
        reportes_menu.add_command(label="Analizar Excel", command=self.abrir_analizador_excel)
        
        ayuda_menu = tk.Menu(menubar, bg=self.color_surface, fg=self.color_text,
                            activebackground=self.color_primary, activeforeground=self.color_surface,
                            tearoff=0, font=('Segoe UI', 9))
        menubar.add_cascade(label="❓ Ayuda", menu=ayuda_menu)
        ayuda_menu.add_command(label="Acerca de", command=self.mostrar_acerca_de)
        
        # Frame principal con fondo mejorado
        marco_principal = ttk.Frame(self.root, style='TFrame')
        marco_principal.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)
        
        # Encabezado mejorado
        marco_encabezado = ttk.Frame(marco_principal)
        marco_encabezado.pack(fill=tk.X, pady=(0, 20))
        
        etiqueta_encabezado = ttk.Label(marco_encabezado, text="📦 Sistema de Gestión de Inventario", 
                                 style='Header.TLabel')
        etiqueta_encabezado.pack(side=tk.LEFT)
        
        # Contenedor principal (3 columnas)
        contenedor = ttk.Frame(marco_principal)
        contenedor.pack(fill=tk.BOTH, expand=True)
        
        # Frame izquierdo - Formulario
        marco_izquierdo = ttk.LabelFrame(contenedor, text="📝 Datos del Producto", padding=18)
        marco_izquierdo.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 16), ipady=12)
        marco_izquierdo.config(relief=tk.FLAT)
        
        # Campos del formulario con mejor espaciado
        etiquetas_valores = [
            ('Nombre:', 'nombre_entrada', 25),
            ('Descripción:', 'descripcion_texto', None),
            ('Cantidad:', 'cantidad_entrada', 25),
            ('Precio Unitario:', 'precio_entrada', 25),
            ('Proveedor:', 'proveedor_entrada', 25),
        ]
        
        fila = 0
        for texto_etiqueta, atributo, ancho in etiquetas_valores:
            etiqueta = ttk.Label(marco_izquierdo, text=texto_etiqueta, style='TLabel')
            etiqueta.grid(row=fila, column=0, sticky=tk.W, pady=10, padx=(0, 12))
            
            if atributo == 'descripcion_texto':
                widget_texto = tk.Text(marco_izquierdo, width=25, height=4, font=('Segoe UI', 9), 
                                      relief=tk.FLAT, borderwidth=1, bg=self.color_surface,
                                      fg=self.color_text, insertbackground=self.color_primary)
                widget_texto.grid(row=fila, column=1, pady=10, sticky=tk.EW)
                setattr(self, atributo, widget_texto)
            else:
                entrada = ttk.Entry(marco_izquierdo, width=ancho)
                entrada.grid(row=fila, column=1, pady=10, sticky=tk.EW)
                setattr(self, atributo, entrada)
            
            fila += 1
        
        
        marco_botones = ttk.Frame(marco_izquierdo)
        marco_botones.grid(row=fila, column=0, columnspan=2, pady=24, sticky=tk.EW)
        
        btn_crear = ttk.Button(marco_botones, text="➕ Crear", command=self.crear_producto, style='Create.TButton')
        btn_crear.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        btn_actualizar = ttk.Button(marco_botones, text="✏️ Actualizar", command=self.actualizar_producto, style='Update.TButton')
        btn_actualizar.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        btn_eliminar = ttk.Button(marco_botones, text="🗑️ Eliminar", command=self.eliminar_producto, style='Delete.TButton')
        btn_eliminar.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        btn_limpiar = ttk.Button(marco_botones, text="🔄 Limpiar", command=self.limpiar_campos)
        btn_limpiar.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        
        contenedor_derecho = ttk.Frame(contenedor)
        contenedor_derecho.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        
        marco_tabla = ttk.LabelFrame(contenedor_derecho, text="📦 Productos Registrados", padding=12)
        marco_tabla.pack(fill=tk.BOTH, expand=True, padx=(0, 0), pady=(0, 16))
        marco_tabla.config(relief=tk.FLAT)
        
        desplazador = ttk.Scrollbar(marco_tabla)
        desplazador.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree = ttk.Treeview(
            marco_tabla,
            columns=('ID', 'Nombre', 'Cantidad', 'Precio', 'Proveedor'),
            height=15,
            yscrollcommand=desplazador.set,
            show='headings'
        )
        desplazador.config(command=self.tree.yview)
        
        # Configurar columnas con mejor ancho
        self.tree.column('ID', anchor=tk.CENTER, width=50)
        self.tree.column('Nombre', anchor=tk.W, width=250)
        self.tree.column('Cantidad', anchor=tk.CENTER, width=100)
        self.tree.column('Precio', anchor=tk.CENTER, width=120)
        self.tree.column('Proveedor', anchor=tk.W, width=200)
        
        # Encabezados mejorados
        self.tree.heading('ID', text='ID', anchor=tk.CENTER)
        self.tree.heading('Nombre', text='Nombre', anchor=tk.W)
        self.tree.heading('Cantidad', text='Cantidad', anchor=tk.CENTER)
        self.tree.heading('Precio', text='Precio Unitario', anchor=tk.CENTER)
        self.tree.heading('Proveedor', text='Proveedor', anchor=tk.W)
        
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        self.tree.bind('<Double-1>', self.cargar_producto_seleccionado)
        
        # Frame de movimientos mejorado
        marco_movimientos = ttk.LabelFrame(contenedor_derecho, text="➡️ Movimiento de Inventario", padding=14)
        marco_movimientos.pack(fill=tk.X, pady=(0, 16))
        marco_movimientos.config(relief=tk.FLAT)
        
        marco_mov_interno = ttk.Frame(marco_movimientos)
        marco_mov_interno.pack(fill=tk.X)
        
        ttk.Label(marco_mov_interno, text="Tipo:", style='TLabel').pack(side=tk.LEFT, padx=6)
        self.tipo_movimiento = ttk.Combobox(marco_mov_interno, values=['📥 Entrada', '📤 Salida'], width=12, state='readonly')
        self.tipo_movimiento.pack(side=tk.LEFT, padx=6)
        
        ttk.Label(marco_mov_interno, text="Cantidad:", style='TLabel').pack(side=tk.LEFT, padx=6)
        self.cantidad_movimiento = ttk.Entry(marco_mov_interno, width=12)
        self.cantidad_movimiento.pack(side=tk.LEFT, padx=6)
        
        ttk.Button(marco_mov_interno, text="✔️ Registrar", command=self.registrar_movimiento).pack(side=tk.LEFT, padx=6)
        
        # Frame de estadísticas mejorado
        marco_estadisticas = ttk.LabelFrame(contenedor_derecho, text="📈 Estadísticas en Tiempo Real", padding=14)
        marco_estadisticas.pack(fill=tk.X)
        marco_estadisticas.config(relief=tk.FLAT)
        
        self.etiqueta_estadisticas = ttk.Label(marco_estadisticas, text="", style='Stats.TLabel')
        self.etiqueta_estadisticas.pack(fill=tk.X)
        
        self.actualizar_estadisticas()
    
    def cargar_productos(self):
        """Cargar productos en la tabla"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        productos = self.db.obtener_productos()
        for producto in productos:
            self.tree.insert(
                '',
                tk.END,
                values=(
                    producto['id'],
                    producto['nombre'],
                    producto['cantidad'],
                    f"${float(producto['precio_unitario']):.2f}",
                    producto['proveedor'] if producto['proveedor'] else 'N/A'
                )
            )
    
    def cargar_producto_seleccionado(self, evento):
        """Cargar datos del producto seleccionado en el formulario"""
        seleccion = self.tree.selection()
        if not seleccion:
            return
        
        elemento = self.tree.item(seleccion[0])
        id_producto = elemento['values'][0]
        
        producto = self.db.obtener_producto(id_producto)
        if producto:
            self.producto_seleccionado = id_producto
            self.nombre_entrada.delete(0, tk.END)
            self.nombre_entrada.insert(0, producto['nombre'])
            
            self.descripcion_texto.delete('1.0', tk.END)
            self.descripcion_texto.insert('1.0', producto['descripcion'] if producto['descripcion'] else '')
            
            self.cantidad_entrada.delete(0, tk.END)
            self.cantidad_entrada.insert(0, str(producto['cantidad']))
            
            self.precio_entrada.delete(0, tk.END)
            self.precio_entrada.insert(0, str(producto['precio_unitario']))
            
            self.proveedor_entrada.delete(0, tk.END)
            self.proveedor_entrada.insert(0, producto['proveedor'] if producto['proveedor'] else '')
    
    def crear_producto(self):
        """Crear nuevo producto"""
        try:
            nombre = self.nombre_entrada.get()
            descripcion = self.descripcion_texto.get('1.0', tk.END).strip()
            cantidad = int(self.cantidad_entrada.get())
            precio = float(self.precio_entrada.get())
            proveedor = self.proveedor_entrada.get()
            
            if not nombre:
                messagebox.showwarning("⚠️ Validación", "El nombre del producto es requerido")
                return
            
            if precio < 0 or cantidad < 0:
                messagebox.showwarning("⚠️ Validación", "Cantidad y Precio no pueden ser negativos")
                return
            
            exito, mensaje = self.db.crear_producto(nombre, descripcion, cantidad, precio, proveedor)
            if exito:
                messagebox.showinfo("✅ Éxito", f"Producto creado exitosamente:\n{nombre}")
                self.limpiar_campos()
                self.cargar_productos()
                self.actualizar_estadisticas()
            else:
                messagebox.showerror("❌ Error", mensaje)
        except ValueError:
            messagebox.showerror("❌ Error de Validación", "Verifique que:\n• Cantidad sea un número entero\n• Precio sea un número decimal")
    
    def actualizar_producto(self):
        """Actualizar producto seleccionado"""
        if not self.producto_seleccionado:
            messagebox.showwarning("⚠️ Validación", "Seleccione un producto de la tabla")
            return
        
        try:
            nombre = self.nombre_entrada.get()
            descripcion = self.descripcion_texto.get('1.0', tk.END).strip()
            cantidad = int(self.cantidad_entrada.get())
            precio = float(self.precio_entrada.get())
            proveedor = self.proveedor_entrada.get()
            
            exito, mensaje = self.db.actualizar_producto(
                self.producto_seleccionado, nombre, descripcion, cantidad, precio, proveedor
            )
            if exito:
                messagebox.showinfo("✅ Éxito", mensaje)
                self.limpiar_campos()
                self.cargar_productos()
                self.actualizar_estadisticas()
            else:
                messagebox.showerror("❌ Error", mensaje)
        except ValueError:
            messagebox.showerror("❌ Error de Validación", "Cantidad debe ser número entero y Precio debe ser decimal")
    
    def eliminar_producto(self):
        """Eliminar producto seleccionado"""
        if not self.producto_seleccionado:
            messagebox.showwarning("⚠️ Validación", "Seleccione un producto de la tabla")
            return
        
        if messagebox.askyesno("⚠️ Confirmación", "¿Está seguro que desea eliminar este producto?"):
            exito, mensaje = self.db.eliminar_producto(self.producto_seleccionado)
            if exito:
                messagebox.showinfo("✅ Éxito", mensaje)
                self.limpiar_campos()
                self.cargar_productos()
                self.actualizar_estadisticas()
            else:
                messagebox.showerror("❌ Error", mensaje)
    
    def limpiar_campos(self):
        """Limpiar los campos del formulario"""
        self.nombre_entrada.delete(0, tk.END)
        self.descripcion_texto.delete('1.0', tk.END)
        self.cantidad_entrada.delete(0, tk.END)
        self.precio_entrada.delete(0, tk.END)
        self.proveedor_entrada.delete(0, tk.END)
        self.producto_seleccionado = None
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())
    
    def registrar_movimiento(self):
        """Registrar movimiento de inventario"""
        try:
            seleccion = self.tree.selection()
            if not seleccion:
                messagebox.showwarning("⚠️ Validación", "Seleccione un producto de la tabla")
                return
            
            elemento = self.tree.item(seleccion[0])
            id_producto = elemento['values'][0]
            
            valor_tipo = self.tipo_movimiento.get()
            if not valor_tipo:
                messagebox.showwarning("⚠️ Validación", "Seleccione tipo de movimiento")
                return
            
            # Extraer el tipo sin el emoji
            tipo = valor_tipo.split(' ')[-1]
            cantidad = int(self.cantidad_movimiento.get())
            
            exito, mensaje = self.db.registrar_movimiento(id_producto, tipo, cantidad)
            if exito:
                messagebox.showinfo("✅ Éxito", mensaje)
                self.cantidad_movimiento.delete(0, tk.END)
                self.tipo_movimiento.set('')
                self.cargar_productos()
                self.actualizar_estadisticas()
            else:
                messagebox.showerror("❌ Error", mensaje)
        except ValueError:
            messagebox.showerror("❌ Error de Validación", "La cantidad debe ser un número entero")
    
    def mostrar_acerca_de(self):
        """Mostrar información acerca de la aplicación"""
        messagebox.showinfo(
            "ℹ️ Acerca de",
            "📦 Sistema de Gestión de Inventario\n\n"
            "Versión: 2.0\n"
            "Desarrollado con Python y Tkinter\n\n"
            "Características:\n"
            "  • Gestión completa de inventario\n"
            "  • Base de datos MySQL\n"
            "  • Reportes en PDF\n"
            "  • Estadísticas en tiempo real\n\n"
            "© 2026 - Equipo de Desarrollo"
        )
    
    def actualizar_estadisticas(self):
        """Actualizar estadísticas mostradas con formato profesional"""
        estadisticas = self.db.obtener_estadisticas()
        total_productos = estadisticas.get('total_productos', 0)
        stock_total = estadisticas.get('stock_total', 0)
        valor_total = estadisticas.get('valor_total', 0)
        bajo_stock = estadisticas.get('bajo_stock', 0)
        
        # Crear texto con emojis y formato profesional
        texto = (
            f"  📊 Productos: {total_productos}  │  "
            f"📦 Stock Total: {stock_total}  │  "
            f"💰 Valor Total: ${valor_total:.2f}  │  "
            f"⚠️ Bajo Stock: {bajo_stock}"
        )
        self.etiqueta_estadisticas.config(text=texto)
    
    def generar_reporte_inventario(self):
        """Generar reporte de inventario"""
        productos = self.db.obtener_productos()
        if not productos:
            messagebox.showwarning("⚠️ Advertencia", "No hay productos registrados para generar reporte")
            return
        
        exito, mensaje = self.gen_reportes.generar_reporte_inventario(productos)
        if exito:
            messagebox.showinfo("✅ Éxito", f"Reporte de inventario generado:\n{mensaje}")
        else:
            messagebox.showerror("❌ Error", mensaje)
    
    def generar_reporte_movimientos(self):
        """Generar reporte de movimientos"""
        movimientos = self.db.obtener_movimientos()
        if not movimientos:
            messagebox.showwarning("⚠️ Advertencia", "No hay movimientos registrados para generar reporte")
            return
        
        productos = self.db.obtener_productos()
        dict_productos = {p['id']: p for p in productos}
        
        exito, mensaje = self.gen_reportes.generar_reporte_movimientos(movimientos, dict_productos)
        if exito:
            messagebox.showinfo("✅ Éxito", f"Reporte de movimientos generado:\n{mensaje}")
        else:
            messagebox.showerror("❌ Error", mensaje)
    
    def generar_reporte_estadisticas(self):
        """Generar reporte de estadísticas"""
        estadisticas = self.db.obtener_estadisticas()
        exito, mensaje = self.gen_reportes.generar_reporte_estadisticas(estadisticas)
        if exito:
            messagebox.showinfo("✅ Éxito", f"Reporte de estadísticas generado:\n{mensaje}")
        else:
            messagebox.showerror("❌ Error", mensaje)

    def exportar_inventario_excel(self):
        try:
            productos = self.db.obtener_productos()
            if not productos:
                messagebox.showwarning("⚠️ Advertencia", "No hay productos para exportar")
                return
            
            success, resultado = self.excel_exporter.exportar_inventario(productos)
            if success:
                messagebox.showinfo("✅ Éxito", f"Inventario exportado correctamente:\n{resultado}")
            else:
                messagebox.showerror("❌ Error", resultado)
        except Exception as err:
            messagebox.showerror("❌ Error", f"Error al exportar inventario: {str(err)}")
    
    def exportar_movimientos_excel(self):
        try:
            movimientos = self.db.obtener_movimientos()
            if not movimientos:
                messagebox.showwarning("⚠️ Advertencia", "No hay movimientos para exportar")
                return
            
            productos = self.db.obtener_productos()
            productos_dict = {p['id']: p for p in productos}
            
            success, resultado = self.excel_exporter.exportar_movimientos(movimientos, productos_dict)
            if success:
                messagebox.showinfo("✅ Éxito", f"Movimientos exportados correctamente:\n{resultado}")
            else:
                messagebox.showerror("❌ Error", resultado)
        except Exception as err:
            messagebox.showerror("❌ Error", f"Error al exportar movimientos: {str(err)}")
    
    def exportar_completo_excel(self):
        try:
            productos = self.db.obtener_productos()
            movimientos = self.db.obtener_movimientos()
            
            if not productos and not movimientos:
                messagebox.showwarning("⚠️ Advertencia", "No hay datos para exportar")
                return
            
            productos_dict = {p['id']: p for p in productos}
            
            success, resultado = self.excel_exporter.exportar_completo(productos, movimientos, productos_dict)
            if success:
                messagebox.showinfo("✅ Éxito", f"Datos completos exportados correctamente:\n{resultado}")
            else:
                messagebox.showerror("❌ Error", resultado)
        except Exception as err:
            messagebox.showerror("❌ Error", f"Error al exportar datos: {str(err)}")

    def abrir_ventana_graficos(self):
        win = tk.Toplevel(self.root)
        win.title("📈 Visualización de Estadísticas")
        win.geometry("1000x700")
        """Abrir ventana con gráficos interactivos embebidos para análisis de datos"""
        # Crear ventana hija
        ventana = tk.Toplevel(self.root)
        ventana.title("📈 Visualización de Estadísticas")
        ventana.geometry("1000x700")
        ventana.configure(bg=self.color_bg)

        # Header de la ventana
        encabezado = ttk.Label(ventana, text="📈 Análisis y Visualización de Datos", 
                          style='Header.TLabel')
        encabezado.pack(pady=12, padx=12, fill=tk.X)

        # Notebook para pestañas
        cuaderno = ttk.Notebook(ventana)
        cuaderno.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        # Pestaña 1: Stock por producto (top 10)
        pestana1 = ttk.Frame(cuaderno)
        cuaderno.add(pestana1, text="📦 Stock por Producto")

        productos = self.db.obtener_productos()
        # Ordenar por cantidad y tomar top 10
        productos_ordenados = sorted(productos, key=lambda p: p.get('cantidad', 0), reverse=True)
        superior = productos_ordenados[:10]
        etiquetas = [p['nombre'] for p in superior]
        valores = [p['cantidad'] for p in superior]

        fig1, ax1 = plt.subplots(figsize=(8, 4), facecolor=self.color_bg)
        ax1.set_facecolor(self.color_surface)
        ax1.barh(etiquetas[::-1], valores[::-1], color=self.color_secondary, edgecolor=self.color_border)
        ax1.set_title('Top 10 productos por cantidad', fontsize=12, fontweight='bold', color=self.color_text, pad=15)
        ax1.set_xlabel('Cantidad', fontsize=10, color=self.color_text)
        ax1.tick_params(colors=self.color_text)
        for spine in ax1.spines.values():
            spine.set_edgecolor(self.color_border)
        fig1.tight_layout()

        lienzo1 = FigureCanvasTkAgg(fig1, master=pestana1)
        lienzo1.draw()
        lienzo1.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # Pestaña 2: Distribución por proveedor (por stock total)
        pestana2 = ttk.Frame(cuaderno)
        cuaderno.add(pestana2, text="🏭 Distribución por Proveedor")

        stock_proveedor = {}
        for p in productos:
            prov = p.get('proveedor') or 'Sin proveedor'
            stock_proveedor[prov] = stock_proveedor.get(prov, 0) + (p.get('cantidad') or 0)

        proveedores = list(stock_proveedor.keys())
        stocks = list(stock_proveedor.values())

        fig2, ax2 = plt.subplots(figsize=(6, 6), facecolor=self.color_bg)
        ax2.set_facecolor(self.color_surface)
        colores = [self.color_primary, self.color_secondary, self.color_warning, '#8B5CF6', '#EC4899']
        colores = (colores * ((len(proveedores) // len(colores)) + 1))[:len(proveedores)]
        if any(stocks):
            ax2.pie(stocks, labels=proveedores, autopct='%1.1f%%', startangle=140, 
                   colors=colores, textprops={'color': self.color_text})
            ax2.set_title('Distribución del stock por proveedor', fontsize=12, fontweight='bold', 
                         color=self.color_text, pad=15)
        else:
            ax2.text(0.5, 0.5, 'No hay datos', ha='center', va='center', color=self.color_text_muted)
        fig2.tight_layout()

        lienzo2 = FigureCanvasTkAgg(fig2, master=pestana2)
        lienzo2.draw()
        lienzo2.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # Pestaña 3: Movimientos últimos 30 días (netos por día)
        pestana3 = ttk.Frame(cuaderno)
        cuaderno.add(pestana3, text="📈 Movimientos (30 días)")

        movimientos = self.db.obtener_movimientos()
        hoy = datetime.now().date()
        fecha_inicio = hoy - timedelta(days=29)

        # Agregar neto por día
        neto_por_fecha = {}
        for movimiento in movimientos:
            fecha = movimiento.get('fecha')
            if not fecha:
                continue
            fecha_convertida = fecha.date()
            if fecha_convertida < fecha_inicio or fecha_convertida > hoy:
                continue
            tipo = (movimiento.get('tipo_movimiento') or '').lower()
            cantidad = int(movimiento.get('cantidad') or 0)
            neto_por_fecha[fecha_convertida] = neto_por_fecha.get(fecha_convertida, 0) + (cantidad if 'entrada' in tipo else -cantidad)

        # Crear listas ordenadas por fecha
        fechas = [fecha_inicio + timedelta(days=i) for i in range(30)]
        netos = [neto_por_fecha.get(d, 0) for d in fechas]

        fig3, ax3 = plt.subplots(figsize=(9, 3.5), facecolor=self.color_bg)
        ax3.set_facecolor(self.color_surface)
        ax3.bar(fechas, netos, color=self.color_primary, edgecolor=self.color_border)
        ax3.set_title('Movimiento neto por día (últimos 30 días)', fontsize=12, fontweight='bold', 
                     color=self.color_text, pad=15)
        ax3.set_xlabel('Fecha', fontsize=10, color=self.color_text)
        ax3.set_ylabel('Cantidad neta', fontsize=10, color=self.color_text)
        ax3.tick_params(colors=self.color_text)
        for spine in ax3.spines.values():
            spine.set_edgecolor(self.color_border)
        ax3.grid(axis='y', alpha=0.2, color=self.color_border)
        fig3.autofmt_xdate(rotation=45)
        fig3.tight_layout()

        lienzo3 = FigureCanvasTkAgg(fig3, master=pestana3)
        lienzo3.draw()
        lienzo3.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

    def abrir_analizador_excel(self):
        """Abrir analizador de hojas Excel (módulo separado)."""
        analyzer = ExcelAnalyzer(self.root)
        analyzer.open_window()
    
    def cerrar(self):
        """Cerrar la aplicación"""
        self.db.disconnect()
        self.root.quit()

if __name__ == "__main__":
    root = tk.Tk()
    app = InventoryManagementApp(root)
    root.protocol("WM_DELETE_WINDOW", app.cerrar)
    root.mainloop()

