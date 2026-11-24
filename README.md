# JARVIS StarkLab

JARVIS StarkLab es un compilador escrito en Python que implementa
un lenguaje propio mediante un analizador léxico, un analizador sintáctico,
un analizador semántico y un ejecutor de programas. Incluye una interfaz
gráfica desarrollada con PyQt.

## Requisitos

- Python 3.14 o una versión compatible
- PLY
- PyQt5 o PyQt6

## Instalación

```powershell
python -m pip install ply PyQt6
```

El proyecto también puede utilizar PyQt5 si PyQt6 no está disponible.

## Ejecución

Para iniciar la interfaz gráfica:

```powershell
python app.py
```

Para ejecutar las fases del lenguaje desde la consola:

```powershell
python lexer.py
python parser.py
python asemantico.py
python ejecutor.py
```

## Funcionalidades

- Variables y tipos básicos
- Operaciones aritméticas y comparaciones
- Condiciones `si` y `sino`
- Ciclos `repetir` y `mientras`
- Acciones con parámetros
- Interfaz con editor de código, consola y visualización del AST
