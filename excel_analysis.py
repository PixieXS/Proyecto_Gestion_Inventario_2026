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

        self._create_window()

    def _create_window(self):
        """Crear la ventana completa con todos los widgets."""
        self.window = tk.Toplevel(self.master)
        self.window.title("📊 Analizador de Excel")
        self.window.geometry("1200x750")
        # Arreglando: Trae la ventana hacia el frente y no como antes que hacia atras xd
        self.window.lift()
        self.window.focus_force()
        self.window.grab_set()  # Evita que quede atras de la ventana principal

        top_frame = ttk.Frame(self.window)
        top_frame.pack(fill=tk.X, padx=10, pady=8)

        load_btn = ttk.Button(top_frame, text="📂 Cargar archivo Excel", command=self.load_file)
        load_btn.pack(side=tk.LEFT)

        self.file_label = ttk.Label(top_frame, text="Ningún archivo cargado")
        self.file_label.pack(side=tk.LEFT, padx=10)

        middle = ttk.PanedWindow(self.window, orient=tk.HORIZONTAL)
        middle.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        left_frame = ttk.LabelFrame(middle, text="Previsualización de datos")
        middle.add(left_frame, weight=2)

        self.tree = ttk.Treeview(left_frame, height=20)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        vsb = ttk.Scrollbar(left_frame, orient="vertical", command=self.tree.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=vsb.set)

        right_frame = ttk.LabelFrame(middle, text="Opciones de gráfico")
        middle.add(right_frame, weight=1)

        ttk.Label(right_frame, text="Eje X (opcional):").pack(anchor=tk.W, pady=(10, 0), padx=6)
        self.x_combo = ttk.Combobox(right_frame, state='readonly', width=25)
        self.x_combo.pack(fill=tk.X, padx=6, pady=(0, 8))

        ttk.Label(right_frame, text="Columnas Y:").pack(anchor=tk.W, padx=6)
        self.y_list = tk.Listbox(right_frame, selectmode=tk.MULTIPLE, exportselection=False,
                                  height=8, width=30)
        self.y_list.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 8))

        ttk.Label(right_frame, text="Tipo de gráfico:").pack(anchor=tk.W, padx=6)
        self.type_combo = ttk.Combobox(right_frame,
                                        values=['Line', 'Bar', 'Scatter', 'Pie'],
                                        state='readonly', width=25)
        self.type_combo.pack(fill=tk.X, padx=6, pady=(0, 8))
        self.type_combo.set('Bar')

        ttk.Button(right_frame, text="📈 Generar gráfico", command=self.generate_plot).pack(
            fill=tk.X, padx=6, pady=(0, 4))
        ttk.Button(right_frame, text="🗑️ Limpiar gráfico", command=self.clear_plot).pack(
            fill=tk.X, padx=6)

        self.fig_frame = None

    def open_window(self):
        """Compatibilidad con código anterior."""
        if self.window is None:
            self._create_window()
        else:
            # Arreglando: Si la ventana ya existe, traerla al frente
            self.window.lift()
            self.window.focus_force()

    def load_file(self):
        path = filedialog.askopenfilename(
            parent=self.window,   #Arreglando: parent correcto para que no tape la ventana
            filetypes=[("Excel files", "*.xlsx;*.xls")]
        )
        if not path:
            return
        try:
            if path.endswith('.xlsx'):
                self.df = pd.read_excel(path, engine='openpyxl')
            else:
                self.df = pd.read_excel(path)

            if self.df is None or self.df.empty:
                messagebox.showwarning("Advertencia", "El archivo está vacío.", parent=self.window)
                return

            print(f"[OK] Archivo cargado: {len(self.df)} filas, {len(self.df.columns)} columnas")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el archivo:\n{str(e)}", parent=self.window)
            return

        filename = path.replace('\\', '/').split('/')[-1]

        if self.file_label is not None:
            self.file_label.config(text=f"📄 {filename}")

        self.populate_preview()

        if self.x_combo is not None and self.y_list is not None:
            cols = list(self.df.columns)
            self.x_combo['values'] = [''] + cols
            self.x_combo.set('')
            self.y_list.delete(0, tk.END)
            for c in cols:
                self.y_list.insert(tk.END, c)

        #Arreglando: mostrar el mensaje con parent=self.window para que no tape la ventana
        messagebox.showinfo(
            "✅ Cargado",
            f"Archivo cargado exitosamente.\n{len(self.df)} filas, {len(self.df.columns)} columnas.",
            parent=self.window
        )
        #Arreglando: asegurar que la ventana del analizador siga visible y al frente
        self.window.lift()
        self.window.focus_force()

    def populate_preview(self):
        if self.tree is None or self.df is None or self.df.empty:
            return

        self.tree.delete(*self.tree.get_children())
        self.tree['columns'] = []

        cols = list(self.df.columns)
        self.tree['columns'] = cols
        self.tree['show'] = 'headings'

        for col in cols:
            self.tree.heading(col, text=str(col))
            self.tree.column(col, width=120, anchor=tk.W)

        for _, row in self.df.head(100).iterrows():
            self.tree.insert('', tk.END, values=list(row))

    def generate_plot(self):
        if self.df is None:
            messagebox.showwarning("Advertencia", "Primero cargue un archivo Excel.", parent=self.window)
            return

        y_indices = self.y_list.curselection()
        if not y_indices:
            messagebox.showwarning("Advertencia", "Seleccione al menos una columna Y.", parent=self.window)
            return

        y_cols = [self.y_list.get(i) for i in y_indices]
        x_col = self.x_combo.get()
        chart_type = self.type_combo.get()

        try:
            fig, ax = plt.subplots(figsize=(11, 6))

            for y_col in y_cols:
                try:
                    y_data = pd.to_numeric(self.df[y_col], errors='coerce')
                except Exception:
                    continue

                x_data = self.df[x_col] if x_col and x_col in self.df.columns else range(len(self.df))

                if chart_type == 'Line':
                    ax.plot(x_data, y_data, label=y_col, marker='o', markersize=3)
                elif chart_type == 'Bar':
                    ax.bar(x_data if isinstance(x_data, range) else range(len(x_data)),
                           y_data, label=y_col, alpha=0.7)
                elif chart_type == 'Scatter':
                    ax.scatter(x_data, y_data, label=y_col, alpha=0.6)
                elif chart_type == 'Pie':
                    ax.pie(y_data.dropna(), labels=self.df[x_col] if x_col else None,
                           autopct='%1.1f%%')
                    break

            ax.set_title(f"Grafico: {', '.join(y_cols)}", fontsize=12, fontweight='bold')
            if x_col:
                ax.set_xlabel(x_col)
            # Solo mostrar leyenda si hay artistas con label
            handles, labels = ax.get_legend_handles_labels()
            if handles:
                ax.legend()
            fig.tight_layout()

            #Arreglando: abrir la gráfica en ventana propia para que sea visible
            import tkinter as tk
            win_plot = tk.Toplevel(self.window)
            win_plot.title(f"📊 {', '.join(y_cols)}")
            win_plot.geometry("900x600")
            win_plot.lift()
            win_plot.focus_force()

            from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
            canvas = FigureCanvasTkAgg(fig, master=win_plot)
            canvas.draw()
            toolbar = NavigationToolbar2Tk(canvas, win_plot)
            toolbar.update()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            self.canvas = canvas

        except Exception as e:
            messagebox.showerror("Error", f"Error al generar gráfico:\n{str(e)}", parent=self.window)

    def clear_plot(self):
        if self.canvas:
            plt.close('all')
            self.canvas = None
