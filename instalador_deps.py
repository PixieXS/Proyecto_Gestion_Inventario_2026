import sys
import subprocess
import importlib

DEPENDENCIAS = [
    # (nombre_import, paquete_pip, version_minima)
    ('mysql.connector', 'mysql-connector-python', None),
    ('PIL',             'Pillow',                 None),
    ('reportlab',       'reportlab',              None),
    ('openpyxl',        'openpyxl',               None),
    ('pandas',          'pandas',                 None),
    ('matplotlib',      'matplotlib',             None),
    ('numpy',           'numpy',                  None),
]


def _verificar_dep(nombre_import):
    try:
        importlib.import_module(nombre_import)
        return True
    except ImportError:
        return False


def instalar_dependencias():
    faltantes = []
    for nombre_import, paquete_pip, _ in DEPENDENCIAS:
        if not _verificar_dep(nombre_import):
            faltantes.append((nombre_import, paquete_pip))

    if not faltantes:
        return True  # Todo instalado, arrancar normal

    # Hay dependencias faltantes — mostrar ventana de instalación
    import tkinter as tk
    from tkinter import ttk
    from gui.ui_helpers import configurar_ventana

    root = tk.Tk()
    root.title("Inventoryx — Instalando dependencias")
    root.configure(bg='#0F172A')
    configurar_ventana(
        root,
        width=560,
        height=380,
        min_width=560,
        min_height=380,
        resizable=(False, False),
    )

    # Encabezado
    hdr = tk.Frame(root, bg='#0D1F3C', height=60)
    hdr.pack(fill=tk.X); hdr.pack_propagate(False)
    tk.Label(hdr, text="📦  Instalando componentes necesarios",
             font=("Segoe UI", 12, "bold"),
             bg='#0D1F3C', fg='#E2F0FF').pack(side=tk.LEFT, padx=16, pady=16)

    body = tk.Frame(root, bg='#0F172A')
    body.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)

    tk.Label(body,
             text=f"Se encontraron {len(faltantes)} componente(s) faltante(s).\n"
                   "La instalación es automática y tomará unos segundos.",
             font=("Segoe UI", 9), bg='#0F172A', fg='#7BA7CC',
             justify='left').pack(anchor='w', pady=(0, 12))

    # Label de estado
    lbl_estado = tk.Label(body, text="Preparando...",
                           font=("Segoe UI", 10, "bold"),
                           bg='#0F172A', fg='#E2F0FF')
    lbl_estado.pack(anchor='w', pady=(0, 6))

    # Barra de progreso
    progress = ttk.Progressbar(body, mode='determinate',
                                maximum=len(faltantes), length=460)
    progress.pack(fill=tk.X, pady=(0, 8))

    # Log de instalación
    frm_log = tk.Frame(body, bg='#1E293B')
    frm_log.pack(fill=tk.BOTH, expand=True)
    txt_log = tk.Text(frm_log, height=6,
                       font=("Consolas", 8),
                       bg='#1E293B', fg='#94A3B8',
                       relief='flat', state='disabled',
                       wrap='word')
    sb_log = ttk.Scrollbar(frm_log, command=txt_log.yview)
    txt_log.configure(yscrollcommand=sb_log.set)
    sb_log.pack(side=tk.RIGHT, fill=tk.Y)
    txt_log.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    errores = []
    instalados = [False]  # para comunicar resultado al hilo principal

    def _log(msg, color='#94A3B8'):
        txt_log.configure(state='normal')
        txt_log.insert(tk.END, msg + '\n')
        txt_log.configure(state='disabled')
        txt_log.see(tk.END)
        root.update()

    def _instalar():
        for i, (nombre_import, paquete_pip) in enumerate(faltantes):
            lbl_estado.config(text=f"Instalando: {paquete_pip}...")
            progress['value'] = i
            _log(f"  → pip install {paquete_pip}")
            root.update()

            try:
                resultado = subprocess.run(
                    [sys.executable, '-m', 'pip', 'install', paquete_pip,
                     '--quiet', '--no-warn-script-location'],
                    capture_output=True, text=True, timeout=120)

                if resultado.returncode == 0:
                    _log(f"  ✅ {paquete_pip} instalado correctamente")
                else:
                    err = resultado.stderr.strip()[-200:] if resultado.stderr else "Error desconocido"
                    _log(f"  ❌ Error: {err}")
                    errores.append(paquete_pip)
            except subprocess.TimeoutExpired:
                _log(f"  ❌ Timeout instalando {paquete_pip}")
                errores.append(paquete_pip)
            except Exception as e:
                _log(f"  ❌ {e}")
                errores.append(paquete_pip)

        progress['value'] = len(faltantes)

        if errores:
            lbl_estado.config(
                text=f"⚠️  {len(errores)} componente(s) no se pudieron instalar.",
                fg='#F59E0B')
            _log(f"\n⚠️  Instale manualmente: pip install {' '.join(errores)}")
            tk.Button(body,
                      text="Cerrar (instalar manualmente)",
                      font=("Segoe UI", 9),
                      bg='#EF4444', fg='white',
                      relief='flat', padx=12, pady=6,
                      command=root.destroy).pack(pady=(8, 0))
            instalados[0] = False
        else:
            lbl_estado.config(text="✅  Todo instalado. Iniciando sistema...",
                               fg='#10B981')
            instalados[0] = True
            root.after(1500, root.destroy)

        root.update()

    # Ejecutar instalación después de que la ventana esté visible
    root.after(300, _instalar)
    root.mainloop()

    return instalados[0] or len(errores) == 0
