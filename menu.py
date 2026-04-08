#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Punto de entrada de compatibilidad.
La implementacion principal vive en main.py en la raiz del proyecto.
"""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


_ROOT_MAIN = Path(__file__).resolve().parent.parent / "main.py"
_SPEC = spec_from_file_location("inventoryx_root_main", _ROOT_MAIN)
_ROOT_MODULE = module_from_spec(_SPEC)
_SPEC.loader.exec_module(_ROOT_MODULE)

mostrar_login = _ROOT_MODULE.mostrar_login
main = _ROOT_MODULE.main


if __name__ == "__main__":
    main()
