# J.A.R.V.I.S. — StarkLab Language Editor

## Descripción del proyecto

J.A.R.V.I.S. es un proyecto de compilador e intérprete desarrollado en Python que permite escribir, analizar y ejecutar programas utilizando un lenguaje de programación propio.

El proyecto cuenta con una interfaz gráfica creada mediante PyQt6 y Qt Designer. Desde ella se puede trabajar con archivos de código, realizar análisis léxico, sintáctico y semántico, ejecutar instrucciones y visualizar el árbol de sintaxis abstracta (AST).

## Tecnologías utilizadas

- **Python:** desarrollo de los módulos del compilador.
- **PLY:** implementación de los analizadores léxico y sintáctico.
- **PyQt6:** funcionamiento de la interfaz gráfica.
- **Qt Designer:** diseño de las ventanas.
- **Graphviz:** generación y visualización del árbol AST.
- **QSS:** personalización de los estilos de la aplicación.

## Organización del proyecto

| Archivo            | Descripción                             |
| ------------------ | --------------------------------------- |
| `cijarvis.py`      | Aplicación principal e interfaz gráfica |
| `alexico.py`       | Analizador léxico                       |
| `asintactico.py`   | Analizador sintáctico                   |
| `asemantico.py`    | Analizador semántico                    |
| `ejecutor.py`      | Ejecución de instrucciones              |
| `arbolst.py`       | Generación del árbol AST                |
| `estilosjarvis.py` | Estilos de los temas azul y blanco      |
| `*.ui`             | Diseños de las ventanas en Qt Designer  |
| `pyproject.toml`   | Configuración y dependencias            |
| `uv.lock`          | Versiones resueltas de las dependencias |

## Funcionamiento

El programa permite trabajar con archivos de extensión `.jvs` y realizar diferentes operaciones desde su editor de código.

Entre las características de la versión actual se encuentran la declaración y actualización de variables, operaciones matemáticas, comparaciones, condiciones `si` y `sino`, ciclos `repetir` y `mientras`, acciones con parámetros e instrucciones para imprimir resultados.

El sistema también muestra mensajes de error durante el análisis y permite visualizar el árbol AST generado a partir del programa.


## Prototipo de interfaz en Figma

El diseño de la interfaz gráfica del compilador JARVIS se realizó en Figma, donde se desarrolló el prototipo visual del editor.

El prototipo permite consultar el diseño de la interfaz y su distribución de componentes.

**Enlace al prototipo:**

[Ver prototipo de JARVIS en Figma](https://www.figma.com/design/3Hsktps1QHRyagkvfWuZQK/Prototipo-de-JARVIS?node-id=1-25)


## Interfaz gráfica

Cuenta con un editor de código con pestañas, explorador de archivos, consola de resultados, tabla de variables y panel de análisis.

Incluye dos temas visuales, azul oscuro y blanco, que se pueden seleccionar desde la ventana principal.

## Instalación y ejecución

Para ejecutar el proyecto se necesita Python 3.14 o una versión compatible, además de las dependencias definidas en `pyproject.toml`.

Se recomienda utilizar **uv** para preparar el entorno.

Instalar las dependencias:

`uv sync`

Iniciar la aplicación:

`uv run python cijarvis.py`

Para generar las imágenes del AST también se requiere tener instalado el programa Graphviz y disponible en el sistema.

## Archivos de ejemplo

La carpeta `ejemplos/` contiene archivos `.jvs` para realizar pruebas del lenguaje, incluyendo ejemplos de código válido y código con errores.

## Historial de ejecuciones

JARVIS guarda los resultados de las ejecuciones en `registros.txt`. Este archivo se conserva localmente y está excluido del repositorio mediante `.gitignore`.

## Objetivo

Desarrollar un lenguaje de programación propio que permita comprender y aplicar las etapas de análisis léxico, análisis sintáctico, análisis semántico y ejecución, integrándolas en una aplicación gráfica que facilite las pruebas y la visualización de resultados.

