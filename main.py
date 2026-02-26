#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Sistema de Gestión de Inventario
Autor: Equipo de Desarrollo
Descripción: Aplicación para gestionar inventario de productos con 
             registro, edición, visualización, eliminación y generación de reportes.
"""

import tkinter as tk
from gui import InventoryManagementApp

def main():
    root = tk.Tk()
    try:
        root.iconbitmap('app_icon.ico')
    except:
        pass
    app = InventoryManagementApp(root)
    root.protocol("WM_DELETE_WINDOW", app.cerrar)
    root.mainloop()

if __name__ == "__main__":
    main()
