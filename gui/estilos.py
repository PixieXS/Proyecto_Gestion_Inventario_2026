import tkinter as tk
from tkinter import ttk
from gui.ui_helpers import configurar_ventana

PALETAS = {
    'corporate': {
        'nombre':    'corporate',
        'label':     '🏢 Corporate Blue',
        'primary':   '#2563EB',
        'secondary': '#3B82F6',
        'danger':    '#EF4444',
        'warning':   '#F59E0B',
        'bg':        '#F1F5F9',
        'surface':   '#FFFFFF',
        'text':      '#1E293B',
        'muted':     '#64748B',
        'border':    '#E2E8F0',
        'header_bg': '#1E3A5F',
        'sidebar_bg':'#1E293B',
        'card_bg':   '#FFFFFF',
        'tree_bg':   '#FFFFFF',
        'acc_open':  '#1E3A5F',
        'acc_hover': '#334155',
    },
    'forest': {
        'nombre':    'forest',
        'label':     '🌲 Forest Business',
        'primary':   '#059669',
        'secondary': '#10B981',
        'danger':    '#EF4444',
        'warning':   '#F59E0B',
        'bg':        '#F0FDF4',
        'surface':   '#FFFFFF',
        'text':      '#14532D',
        'muted':     '#6B7280',
        'border':    '#D1FAE5',
        'header_bg': '#064E3B',
        'sidebar_bg':'#022C22',
        'card_bg':   '#FFFFFF',
        'tree_bg':   '#FFFFFF',
        'acc_open':  '#065F46',
        'acc_hover': '#0D3321',
    },
    'slate': {
        'nombre':    'slate',
        'label':     '🪨 Slate & Steel',
        'primary':   '#475569',
        'secondary': '#64748B',
        'danger':    '#DC2626',
        'warning':   '#D97706',
        'bg':        '#F8FAFC',
        'surface':   '#FFFFFF',
        'text':      '#0F172A',
        'muted':     '#64748B',
        'border':    '#CBD5E1',
        'header_bg': '#0F172A',
        'sidebar_bg':'#1E293B',
        'card_bg':   '#FFFFFF',
        'tree_bg':   '#FFFFFF',
        'acc_open':  '#1E293B',
        'acc_hover': '#334155',
    },
    'honduras': {
        'nombre':    'honduras',
        'label':     '🇭🇳 Honduras',
        # Azul bandera hondureña + blanco + acento celeste
        'primary':   '#0F47AF',   # azul bandera
        'secondary': '#1565C0',   # azul más claro
        'danger':    '#C62828',   # rojo para errores
        'warning':   '#F59E0B',
        'bg':        '#F0F4FF',   # blanco con toque azul
        'surface':   '#FFFFFF',
        'text':      '#0A2472',   # azul oscuro para texto
        'muted':     '#5C7AC9',
        'border':    '#B3C6F5',
        'header_bg': '#0F2D6B',   # azul oscuro bandera
        'sidebar_bg':'#0A1F4E',   # azul más profundo
        'card_bg':   '#FFFFFF',
        'tree_bg':   '#FFFFFF',
        'acc_open':  '#0F3580',
        'acc_hover': '#1A3A7A',
    },
}


def aplicar_estilos(root, paleta='corporate'):
    C = PALETAS.get(paleta, PALETAS['corporate']).copy()
    root.config(bg=C['bg'])

    s = ttk.Style()
    s.theme_use('clam')

    s.configure('TFrame',            background=C['bg'])
    s.configure('TLabel',            background=C['bg'],      foreground=C['text'],   font=('Segoe UI', 9))
    s.configure('Header.TLabel',     background=C['bg'],      foreground=C['primary'],font=('Segoe UI', 15, 'bold'))
    s.configure('TLabelframe',       background=C['bg'],      foreground=C['text'],   font=('Segoe UI', 9, 'bold'), padding=2)
    s.configure('TLabelframe.Label', background=C['bg'],      foreground=C['text'])
    s.configure('TEntry',            fieldbackground=C['surface'], foreground=C['text'],   font=('Segoe UI', 9))
    s.configure('TCombobox',         fieldbackground=C['surface'], foreground=C['text'],   font=('Segoe UI', 9))
    s.configure('Treeview',          background=C['tree_bg'], foreground=C['text'],
                fieldbackground=C['tree_bg'], font=('Segoe UI', 9), rowheight=24)
    s.configure('Treeview.Heading',  background=C['primary'], foreground='#FFFFFF',
                font=('Segoe UI', 9, 'bold'), relief='flat')
    s.map('Treeview.Heading', background=[('active', C['secondary'])])
    s.map('Treeview',
          background=[('selected', C['primary'])],
          foreground=[('selected', '#FFFFFF')])
    s.configure('TScrollbar',    background='#475569', troughcolor=C['border'])
    s.configure('TNotebook',     background=C['bg'])
    s.configure('TNotebook.Tab', background=C['surface'], foreground=C['text'], font=('Segoe UI', 9))
    s.map('TNotebook.Tab',
          background=[('selected', C['primary'])],
          foreground=[('selected', '#FFFFFF')])

    for tag, fg, bg, abg in [
        ('Create.TButton',  '#FFFFFF', C['secondary'], C['primary']),
        ('Update.TButton',  '#FFFFFF', C['primary'],   C['secondary']),
        ('Delete.TButton',  '#FFFFFF', C['danger'],    '#DC2626'),
        ('Neutral.TButton', '#FFFFFF', '#475569',      '#334155'),
        ('Warn.TButton',    '#FFFFFF', C['warning'],   '#D97706'),
        ('TButton',         '#FFFFFF', C['primary'],   C['secondary']),
    ]:
        s.configure(tag, font=('Segoe UI', 9, 'bold'), padding=(8, 5))
        s.map(tag,
              background=[('!active', bg), ('active', abg)],
              foreground=[('!active', fg), ('active', fg)])
    return C


def ventana_fullscreen(master, titulo, C):
    """
    Crea un Toplevel maximizado con cierre normal desde la X.
    """
    win = tk.Toplevel(master)
    win.title(titulo)
    win.configure(bg=C['bg'])
    win.grab_set()
    configurar_ventana(win, size='main', min_width=1200, min_height=760, start_maximized=True)
    return win
