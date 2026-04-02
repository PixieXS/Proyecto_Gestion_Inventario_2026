#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ── Instalar dependencias automáticamente si faltan ───────────────────────────
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from instalador_deps import instalar_dependencias
if not instalar_dependencias():
    sys.exit(1)
# ─────────────────────────────────────────────────────────────────────────────

import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timedelta
from database import DatabaseManager
from gui.ui_helpers import configurar_ventana

MAX_INTENTOS = 5
BLOQUEO_MIN  = 10

# Paleta basada en el logo — azul eléctrico + cyan/turquesa
IX = {
    # Panel izquierdo — blanco, letras oscuras
    'left_bg':    '#FFFFFF',
    'left_mid':   '#F0F6FF',
    'accent':     '#00B4BC',   # cyan del logo
    'accent2':    '#1A6FD4',   # azul eléctrico del logo
    'left_text':  '#0F172A',   # negro para títulos
    'left_muted': '#0F172A',  
    'left_sub':   '#0F172A',  
    # Panel derecho
    'bg_dark':    '#060E1A',   # casi negro azulado
    'bg_card':    '#0D1F3C',
    'bg_field':   '#0D1F3C',
    'text':       '#E2F0FF',
    'muted':      '#7BA7CC',
    'border_dim': '#1A3A5C',
    'border_on':  '#00C4CC',
    'danger':     '#FF4D6A',
    'warning':    '#F59E0B',
}


