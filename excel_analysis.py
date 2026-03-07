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
        # Error Corregido Aqui: Se trae la ventana hacia el frente
        self.window.lift()
        self.window.focus_force()
        self.window.grab_set()  # Evita que la ventana abierta quede detrás de la ventana principal

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

        # Insertando Controles para los graficos
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