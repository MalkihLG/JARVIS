import contextlib
import io
import sys
from datetime import datetime
from pathlib import Path

try:
    from PyQt6 import uic
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QColor, QKeySequence, QPixmap, QShortcut, QTextCharFormat, QTextCursor
    from PyQt6.QtWidgets import (
        QApplication,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QTableWidgetItem,
        QWidget,
    )
    QT_VERSION = 6
except ImportError:
    from PyQt5 import uic
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QColor, QKeySequence, QPixmap, QShortcut, QTextCharFormat, QTextCursor
    from PyQt5.QtWidgets import (
        QApplication,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QTableWidgetItem,
        QWidget,
    )
    QT_VERSION = 5

from lexer import lexer
import parser as jarvis_parser
from asemantico import analizar_programa, tabla_simbolos, ErrorSemantico
from ejecutor import EjecutorJARVIS

BASE_DIR = Path(__file__).resolve().parent
UI_FILE = BASE_DIR / "interfaz_starklab.ui"
REGISTROS_FILE = BASE_DIR / "registros.txt"
AST_IMG_FILE = BASE_DIR / "arboles" / "AST_JARVIS.png"


def inferir_tipo_jarvis(nombre_var: str, valor):
    if nombre_var in tabla_simbolos and "tipo" in tabla_simbolos[nombre_var]:
        return str(tabla_simbolos[nombre_var]["tipo"])
    if isinstance(valor, bool):
        return "logico"
    if isinstance(valor, int):
        return "entero"
    if isinstance(valor, float):
        return "decimal"
    if isinstance(valor, str):
        return "cadenita"
    return type(valor).__name__


class StarkLabApp(QMainWindow):
    def __init__(self):
        super().__init__()
        if not UI_FILE.exists():
            QMessageBox.critical(self, "Error", f"No se encontró {UI_FILE}")
            sys.exit(1)

        uic.loadUi(str(UI_FILE), self)

        codigo_inicial = getattr(jarvis_parser, "codigo", "").strip()
        self.txtCodigo.setPlainText(codigo_inicial)

        self._construir_barra_busqueda()
        self._configurar_atajos()

        self.btnEjecutar.clicked.connect(self.ejecutar_mision)
        self.btnLimpiar.clicked.connect(self.limpiar_paneles)

        self.cargar_imagen_ast()

    def _construir_barra_busqueda(self):
        """Agrega una barra compacta de búsqueda arriba del editor de código sin tocar el .ui."""
        self.barraBusqueda = QWidget(self)
        layout = QHBoxLayout(self.barraBusqueda)
        layout.setContentsMargins(0, 0, 0, 2)
        layout.setSpacing(6)

        self.txtBuscar = QLineEdit(self.barraBusqueda)
        self.txtBuscar.setPlaceholderText("Buscar en código... (Ctrl+F)")
        self.txtBuscar.setStyleSheet("""
            QLineEdit {
                background-color: #0f172a;
                color: #e0f2fe;
                border: 1px solid #1e3a5f;
                border-radius: 6px;
                padding: 5px 8px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #38bdf8;
            }
        """)

        btn_estilo = """
            QPushButton {
                background-color: #1e293b;
                color: #7ee8fa;
                border: 1px solid #38bdf8;
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0284c7;
                color: #ffffff;
            }
        """

        self.btnBuscarSig = QPushButton("Siguiente", self.barraBusqueda)
        self.btnBuscarSig.setStyleSheet(btn_estilo)

        self.btnLimpiarBusqueda = QPushButton("Limpiar", self.barraBusqueda)
        self.btnLimpiarBusqueda.setStyleSheet(btn_estilo)

        self.lblEstadoAnalisis = QLabel("ESTADO: LISTO", self.barraBusqueda)
        self.lblEstadoAnalisis.setStyleSheet("""
            QLabel {
                color: #fbbf24;
                font-size: 11px;
                font-weight: bold;
                padding: 2px 6px;
            }
        """)

        layout.addWidget(self.txtBuscar, stretch=2)
        layout.addWidget(self.btnBuscarSig)
        layout.addWidget(self.btnLimpiarBusqueda)
        layout.addWidget(self.lblEstadoAnalisis)

        # Insertar justo antes de txtCodigo dentro de leftLayout si existe
        left_layout = getattr(self, "leftLayout", None)
        if left_layout is not None:
            idx = left_layout.indexOf(self.txtCodigo)
            if idx != -1:
                left_layout.insertWidget(idx, self.barraBusqueda)
            else:
                left_layout.addWidget(self.barraBusqueda)

        self.txtBuscar.textChanged.connect(self.resaltar_coincidencias)
        self.txtBuscar.returnPressed.connect(self.buscar_siguiente)
        self.btnBuscarSig.clicked.connect(self.buscar_siguiente)
        self.btnLimpiarBusqueda.clicked.connect(self.limpiar_busqueda)

    def _configurar_atajos(self):
        atajo_buscar = QShortcut(QKeySequence("Ctrl+F"), self)
        atajo_buscar.activated.connect(self.enfocar_busqueda)

    def enfocar_busqueda(self):
        self.txtBuscar.setFocus()
        self.txtBuscar.selectAll()
        self.resaltar_coincidencias()

    def resaltar_coincidencias(self):
        texto_buscar = self.txtBuscar.text()
        documento = self.txtCodigo.document()

        # Limpiar resaltados previos
        cursor_limpiar = QTextCursor(documento)
        cursor_limpiar.select(QTextCursor.SelectionType.Document if QT_VERSION == 6 else QTextCursor.Document)
        formato_limpio = QTextCharFormat()
        formato_limpio.setBackground(QColor("#0f172a"))
        formato_limpio.setForeground(QColor("#e0f2fe"))
        cursor_limpiar.setCharFormat(formato_limpio)

        if not texto_buscar:
            return

        formato_resaltado = QTextCharFormat()
        formato_resaltado.setBackground(QColor("#eab308"))
        formato_resaltado.setForeground(QColor("#090d16"))

        cursor = QTextCursor(documento)
        while True:
            cursor = documento.find(texto_buscar, cursor)
            if cursor.isNull():
                break
            cursor.mergeCharFormat(formato_resaltado)

    def buscar_siguiente(self):
        texto_buscar = self.txtBuscar.text()
        if not texto_buscar:
            return

        self.resaltar_coincidencias()
        encontrado = self.txtCodigo.find(texto_buscar)
        if not encontrado:
            # Volver al inicio si llegó al final
            cursor_inicio = self.txtCodigo.textCursor()
            cursor_inicio.movePosition(
                QTextCursor.MoveOperation.Start if QT_VERSION == 6 else QTextCursor.Start
            )
            self.txtCodigo.setTextCursor(cursor_inicio)
            self.txtCodigo.find(texto_buscar)

    def limpiar_busqueda(self):
        self.txtBuscar.clear()
        self.resaltar_coincidencias()
        self.txtCodigo.setFocus()

    def _establecer_estado(self, valido: bool, mensaje: str = ""):
        if valido:
            self.lblEstadoAnalisis.setText(f"ESTADO: VÁLIDO {mensaje}".strip())
            self.lblEstadoAnalisis.setStyleSheet(
                "QLabel { color: #34d399; font-size: 11px; font-weight: bold; }"
            )
        else:
            self.lblEstadoAnalisis.setText(f"ESTADO: CON ERRORES {mensaje}".strip())
            self.lblEstadoAnalisis.setStyleSheet(
                "QLabel { color: #f87171; font-size: 11px; font-weight: bold; }"
            )

    def cargar_imagen_ast(self):
        if AST_IMG_FILE.exists():
            pixmap = QPixmap(str(AST_IMG_FILE))
            if not pixmap.isNull():
                ancho = max(200, self.imgArbol.width() - 20)
                alto = max(140, self.imgArbol.height() - 20)
                aspecto = Qt.AspectRatioMode.KeepAspectRatio if QT_VERSION == 6 else Qt.KeepAspectRatio
                suave = (
                    Qt.TransformationMode.SmoothTransformation
                    if QT_VERSION == 6
                    else Qt.SmoothTransformation
                )
                self.imgArbol.setPixmap(pixmap.scaled(ancho, alto, aspecto, suave))
        else:
            self.imgArbol.setText("Coloca arboles/AST_JARVIS.png para visualizar el AST")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.cargar_imagen_ast()

    def limpiar_paneles(self):
        self.txtConsola.clear()
        self.tblVariables.setRowCount(0)
        self.lblEstadoAnalisis.setText("ESTADO: LISTO")
        self.lblEstadoAnalisis.setStyleSheet("QLabel { color: #fbbf24; font-size: 11px; font-weight: bold; }")

    def guardar_registro(self, estado_texto: str, salida_texto: str, variables_dict: dict, ejecutor_instancia: EjecutorJARVIS):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(REGISTROS_FILE, "a", encoding="utf-8") as f:
            f.write(f"================ [{timestamp}] ================\n")
            f.write(f"ESTADO: {estado_texto}\n")
            f.write("VARIABLES:\n")
            if variables_dict:
                for k, v in variables_dict.items():
                    tipo_str = inferir_tipo_jarvis(k, v)
                    val_str = ejecutor_instancia.convertir_salida(v)
                    f.write(f"  - {k} ({tipo_str}): {val_str}\n")
            else:
                f.write("  (sin variables en memoria)\n")
            f.write("SALIDA:\n")
            f.write((salida_texto.strip() or "(sin salida)") + "\n\n")

    def ejecutar_mision(self):
        codigo_fuente = self.txtCodigo.toPlainText()
        buffer_salida = io.StringIO()
        ejecutor_instancia = EjecutorJARVIS()
        es_valido = True

        try:
            lexer.lineno = 1

            with contextlib.redirect_stdout(buffer_salida):
                arbol = jarvis_parser.parser.parse(codigo_fuente, lexer=lexer)
                if arbol is None:
                    raise SyntaxError("No se pudo construir el AST (revisa la sintaxis).")

                analizar_programa(arbol)
                ejecutor_instancia.ejecutar_programa(arbol)

            # Verificar si hubo errores léxicos impresos en stdout
            salida_parcial = buffer_salida.getvalue()
            if "Error lexico" in salida_parcial:
                es_valido = False

        except (
            SyntaxError,
            ErrorSemantico,
            ValueError,
            TypeError,
            ZeroDivisionError,
            RecursionError,
            Exception,
        ) as error:
            es_valido = False
            buffer_salida.write(f"\n========== ERROR JARVIS ==========\n{error}\n")

        self._establecer_estado(es_valido)

        vars_dict = ejecutor_instancia.variables
        filas = []
        for nombre, valor in vars_dict.items():
            tipo_str = inferir_tipo_jarvis(nombre, valor)
            valor_str = ejecutor_instancia.convertir_salida(valor)
            filas.append((nombre, tipo_str, valor_str))

        self.tblVariables.setRowCount(len(filas))
        for idx, (nombre, tipo_str, valor_str) in enumerate(filas):
            self.tblVariables.setItem(idx, 0, QTableWidgetItem(str(nombre)))
            self.tblVariables.setItem(idx, 1, QTableWidgetItem(str(tipo_str)))
            self.tblVariables.setItem(idx, 2, QTableWidgetItem(str(valor_str)))

        header = self.tblVariables.horizontalHeader()
        modo_stretch = QHeaderView.ResizeMode.Stretch if QT_VERSION == 6 else QHeaderView.Stretch
        modo_contenido = (
            QHeaderView.ResizeMode.ResizeToContents
            if QT_VERSION == 6
            else QHeaderView.ResizeToContents
        )
        header.setSectionResizeMode(0, modo_stretch)
        header.setSectionResizeMode(1, modo_contenido)
        header.setSectionResizeMode(2, modo_stretch)

        salida_texto = buffer_salida.getvalue().strip()
        self.txtConsola.setPlainText(salida_texto)
        self.guardar_registro(self.lblEstadoAnalisis.text(), salida_texto, vars_dict, ejecutor_instancia)
        self.cargar_imagen_ast()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = StarkLabApp()
    ventana.show()
    sys.exit(app.exec() if QT_VERSION == 6 else app.exec_())