import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

class ExcelAnalyzer:
    """Ventana para cargar un archivo Excel, previsualizar datos y generar gráficos."""
    def __init__(self, master):
        self.master = master
        self.df = None
        self.window = None
        self.canvas = None
        self.tree = None
        self.file_label = None
        self.x_combo = None
        self.y_list = None
        self.type_combo = None
        self.fig_frame = None
        
        # Crear ventana inmediatamente
        self._create_window()

    def _create_window(self):
        """Crear la ventana completa con todos los widgets."""
        self.window = tk.Toplevel(self.master)
        self.window.title("Analizador de Excel")
        self.window.geometry("1200x750")
        
        # TOP: Botón de carga y nombre de archivo
        top_frame = ttk.Frame(self.window)
        top_frame.pack(fill=tk.X, padx=10, pady=8)

        load_btn = ttk.Button(top_frame, text="Cargar archivo Excel", command=self.load_file)
        load_btn.pack(side=tk.LEFT)

        self.file_label = ttk.Label(top_frame, text="Ningún archivo cargado")
        self.file_label.pack(side=tk.LEFT, padx=10)

        # MIDDLE: Horizontal PanedWindow con tree y controles
        middle = ttk.PanedWindow(self.window, orient=tk.HORIZONTAL)
        middle.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # IZQUIERDA: Preview del archivo (tree)
        left_frame = ttk.LabelFrame(middle, text="Previsualización de datos")
        middle.add(left_frame, weight=2)

        self.tree = ttk.Treeview(left_frame, height=20)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        vsb = ttk.Scrollbar(left_frame, orient="vertical", command=self.tree.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=vsb.set)

        # DERECHA: Controles para gráficos
        right_frame = ttk.LabelFrame(middle, text="Opciones de grafico")
        middle.add(right_frame, weight=1)

        ttk.Label(right_frame, text="Eje X (opcional):").pack(anchor=tk.W, pady=(10, 0), padx=6)
        self.x_combo = ttk.Combobox(right_frame, state='readonly', width=25)
        self.x_combo.pack(fill=tk.X, padx=6, pady=(0, 8))

        ttk.Label(right_frame, text="Columnas Y:").pack(anchor=tk.W, pady=(0, 0), padx=6)
        self.y_list = tk.Listbox(right_frame, selectmode=tk.MULTIPLE, exportselection=False, height=8, width=30)
        self.y_list.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 8))

        ttk.Label(right_frame, text="Tipo de grafico:").pack(anchor=tk.W, padx=6)
        self.type_combo = ttk.Combobox(right_frame, values=['Line', 'Bar', 'Scatter', 'Pie'], state='readonly', width=25)
        self.type_combo.pack(fill=tk.X, padx=6, pady=(0, 8))
        self.type_combo.set('Bar')

        gen_btn = ttk.Button(right_frame, text="Generar grafico", command=self.generate_plot)
        gen_btn.pack(fill=tk.X, padx=6, pady=(0, 4))

        clear_btn = ttk.Button(right_frame, text="Limpiar grafico", command=self.clear_plot)
        clear_btn.pack(fill=tk.X, padx=6)

        # BOTTOM: Frame para mostrar gráficos
        bottom_label = ttk.LabelFrame(self.window, text="Grafico")
        bottom_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        self.fig_frame = ttk.Frame(bottom_label)
        self.fig_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        print("[OK] Ventana del analizador Excel creada exitosamente")
        print(f"[DEBUG] fig_frame asignado: {self.fig_frame is not None}")

    def open_window(self):
        """Mantener para compatibilidad con código anterior."""
        if self.window is None:
            self._create_window()

    def load_file(self):
        path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx;*.xls")])
        if not path:
            return
        try:
            # Try reading with openpyxl engine first (for .xlsx)
            if path.endswith('.xlsx'):
                self.df = pd.read_excel(path, engine='openpyxl')
            else:
                self.df = pd.read_excel(path)
            
            # Validate
            if self.df is None or self.df.empty:
                messagebox.showwarning("Advertencia", "El archivo esta vacio.")
                return
            
            print(f"[OK] Archivo cargado: {len(self.df)} filas, {len(self.df.columns)} columnas")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el archivo:\n{str(e)}")
            return
        
        # Update UI
        filename = path.split('\\')[-1] if '\\' in path else path.split('/')[-1]
        
        if self.file_label is not None:
            self.file_label.config(text=filename)
        
        self.populate_preview()
        
        if self.x_combo is not None and self.y_list is not None:
            cols = list(self.df.columns)
            self.x_combo['values'] = [''] + cols
            self.x_combo.set('')
            self.y_list.delete(0, tk.END)
            for c in cols:
                self.y_list.insert(tk.END, c)
        
        messagebox.showinfo("Exito", f"Archivo cargado exitosamente.\n{len(self.df)} filas, {len(self.df.columns)} columnas.")

    def populate_preview(self):
        # Validar que tree exista
        if self.tree is None:
            print("[ERROR] Tree widget no inicializado")
            return
        
        if self.df is None or self.df.empty:
            print("[WARN] DataFrame vacio o None")
            return
        
        # limpiar completamente el tree
        self.tree.delete(*self.tree.get_children())
        for col in self.tree['columns']:
            self.tree.delete(col)
        
        # configurar columnas
        cols = list(self.df.columns)
        self.tree['columns'] = cols
        self.tree['show'] = 'headings'
        
        # Determinar ancho adaptable
        col_width = max(80, min(150, 1200 // max(len(cols), 1)))
        
        for c in cols:
            self.tree.heading(c, text=str(c))
            self.tree.column(c, width=col_width, anchor=tk.W)
        
        # insertar filas (primeras 50)
        for idx, (_, row) in enumerate(self.df.head(50).iterrows()):
            try:
                vals = [str(row.get(c, ''))[:50] for c in cols]
                self.tree.insert('', tk.END, values=vals)
            except Exception as e:
                print(f"[ERROR] Error insertando fila {idx}: {e}")
        
        print(f"[OK] Preview con {min(50, len(self.df))} filas mostradas")

    def clear_plot(self):
        if self.canvas is not None:
            try:
                self.canvas.get_tk_widget().destroy()
                self.canvas = None
                plt.close('all')
                print("[OK] Grafico limpiado")
            except Exception as e:
                print(f"[ERROR] Error limpiando grafico: {e}")

    def generate_plot(self):
        if self.df is None or self.df.empty:
            messagebox.showwarning("Advertencia", "Primero cargue un archivo Excel valido.")
            return
        
        if self.y_list is None or self.x_combo is None or self.type_combo is None:
            messagebox.showerror("Error", "Interfaz no inicializada correctamente.")
            return
        
        x_col = self.x_combo.get()
        y_indices = self.y_list.curselection()
        
        if not y_indices:
            messagebox.showwarning("Advertencia", "Seleccione al menos una columna Y para graficar.")
            return
        
        y_cols = [self.y_list.get(i) for i in y_indices]
        gtype = self.type_combo.get().lower()

        try:
            # Limpiar figuras previas
            plt.close('all')
            
            # Destruir canvas anterior si existe
            if self.canvas is not None:
                try:
                    self.canvas.get_tk_widget().destroy()
                except:
                    pass
                self.canvas = None
            
            # Crear nueva figura
            fig, ax = plt.subplots(figsize=(8, 5), dpi=100)

            if gtype == 'pie':
                if len(y_cols) != 1:
                    messagebox.showwarning("Advertencia", "Grafico de pastel requiere exactamente una columna Y.")
                    return
                
                ycol = y_cols[0]
                series = pd.to_numeric(self.df[ycol], errors='coerce').fillna(0)
                
                if x_col and x_col in self.df.columns:
                    labels = self.df[x_col].astype(str)
                else:
                    labels = [str(i) for i in self.df.index]
                
                grouped = series.groupby(labels).sum()
                
                if grouped.sum() == 0:
                    messagebox.showwarning("Advertencia", "No hay valores numericos validos para graficar.")
                    return
                
                ax.pie(grouped, labels=grouped.index, autopct='%1.1f%%')
                ax.set_title(f'Distribucion de {ycol}')
            else:
                if x_col and x_col in self.df.columns:
                    x_data = self.df[x_col]
                    x_label = x_col
                else:
                    x_data = range(len(self.df))
                    x_label = 'Indice'
                
                for col in y_cols:
                    if col not in self.df.columns:
                        messagebox.showwarning("Advertencia", f"Columna '{col}' no encontrada.")
                        return
                    
                    y_data = pd.to_numeric(self.df[col], errors='coerce')
                    
                    if gtype == 'line':
                        ax.plot(x_data, y_data, label=col, marker='o', linewidth=2)
                    elif gtype == 'bar':
                        ax.bar(x_data, y_data, label=col, alpha=0.7)
                    elif gtype == 'scatter':
                        ax.scatter(x_data, y_data, label=col, alpha=0.6, s=50)
                
                ax.set_xlabel(x_label)
                ax.set_ylabel(','.join(y_cols))
                ax.legend()
                ax.set_title(f'Grafico de {",".join(y_cols)}')
                ax.grid(True, alpha=0.3)

            fig.tight_layout()

            # Embeber canvas en fig_frame
            if self.fig_frame is not None:
                # Crear y embeber canvas
                self.canvas = FigureCanvasTkAgg(fig, master=self.fig_frame)
                self.canvas.draw()
                widget = self.canvas.get_tk_widget()
                widget.pack(fill=tk.BOTH, expand=True)
                
                print(f"[OK] Grafico generado exitosamente: {gtype.title()}")
                messagebox.showinfo("Exito", "Grafico generado correctamente")
            else:
                print("[ERROR] fig_frame no inicializado o es None")
                messagebox.showerror("Error", "No se pudo embeber el grafico")
                
        except Exception as e:
            print(f"[ERROR] Excepcion detallada: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Error generando grafico:\n{str(e)}")
