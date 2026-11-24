from __future__ import annotations

import contextlib
import io
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

from PyQt6 import uic
from PyQt6.QtCore import Qt, QRegularExpression, QTimer
from PyQt6.QtGui import (
    QColor,
    QFont,
    QKeySequence,
    QPixmap,
    QShortcut,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextCursor,
    QTextFormat,
)
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QTableWidgetItem,
    QAbstractItemView,
    QTextEdit,
    QPlainTextEdit,
    QTabBar,
    QStackedWidget,
    QTreeWidgetItem,
    QInputDialog,
)

from estilosjarvis import DARK_QSS, LIGHT_QSS
from alexico import lexer
import asintactico as jarvis_parser
from asemantico import (
    analizar_programa,
    tabla_simbolos,
    ErrorSemantico,
)
from ejecutor import EjecutorJARVIS, ErrorEjecucionJARVIS
from arbolst import generar_ast as generar_ast_principal


BASE_DIR = Path(__file__).resolve().parent
UI_FILE = BASE_DIR / "interfazjarvisazul.ui"
REGISTROS_FILE = BASE_DIR / "registros.txt"
ARBOLES_DIR = BASE_DIR / "arboles"
AST_FILE = ARBOLES_DIR / "AST_JARVIS_NUEVO.png"


def _nombre_tipo(tipo) -> str:
    """Se presenta una descripcion legible de los tipos."""

    if not isinstance(tipo, dict):
        return str(tipo)

    clase = tipo.get("tipo")

    if clase == "personalizado":
        return str(tipo.get("nombre", "desconocido"))

    if clase == "lista":
        return f"lista[{_nombre_tipo(tipo.get('elemento'))}]"

    if clase == "mapa":
        return (
            f"mapa[{_nombre_tipo(tipo.get('clave'))}, "
            f"{_nombre_tipo(tipo.get('valor'))}]"
        )

    return str(clase or "desconocido")


def tipo_jarvis(nombre: str, valor) -> str:
    """Se identifica el tipo mostrado en la tabla de variables."""

    if nombre in tabla_simbolos:
        datos = tabla_simbolos[nombre]

        if "tipo" in datos:
            return _nombre_tipo(datos["tipo"])

    if isinstance(valor, bool):
        return "logico"

    if isinstance(valor, int):
        return "entero"

    if isinstance(valor, float):
        return "decimal"

    if isinstance(valor, str):
        return "cadenita"

    if isinstance(valor, list):
        return "lista"

    if isinstance(valor, dict):
        return "mapa"

    return type(valor).__name__


class ErrorLexicoJARVIS(SyntaxError):
    """Se identifica un error procedente del analizador lexico."""


class ResaltadorJARVIS(QSyntaxHighlighter):
    """Se colorean las instrucciones del editor JARVIS."""

    def __init__(self, documento, dark=True):
        super().__init__(documento)

        self.rules = []
        self.dark = dark
        self.set_dark(dark)

    def set_dark(self, enabled):
        self.dark = enabled
        dark = enabled
        self.rules = []

        def rule(regex, color, bold=False):
            formato = QTextCharFormat()
            formato.setForeground(QColor(color))

            if bold:
                formato.setFontWeight(QFont.Weight.Bold)

            self.rules.append(
                (QRegularExpression(regex), formato)
            )

        rule(
            r"\b(sistema|mision|principal|accion|ejecutar|devolver|"
            r"var|fijo|estado|imprimir|preguntar|alerta|registrar|"
            r"checar|si|sinosi|sino|segun|caso|otro_caso|para|"
            r"mientras|repetir|detener|seguir|en|y|o|negar|div|"
            r"vigilar|proteger|atrapar|lanzar|finalmente|clase|"
            r"crear|este|iniciar|publico|privado|hereda|usar|"
            r"modulo|estructura|enumeracion)\b",
            "#67A9FF" if dark else "#1C60B6",
            True,
        )

        rule(
            r"\b(entero|decimal|cadenita|logico|caracter|"
            r"lista|mapa|vacio|nada)\b",
            "#D7A4FA" if dark else "#9051B8",
            True,
        )

        rule(
            r"\b(si\s+paso|no\s+paso)\b",
            "#69DFB9" if dark else "#147E6D",
        )

        rule(
            r"\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b",
            "#F0B77E" if dark else "#AD5B1E",
        )

        rule(
            r'"[^"\\]*(?:\\.[^"\\]*)*"',
            "#69D4AE" if dark else "#18815F",
        )

        rule(
            r"'([^'\\]|\\.)'",
            "#69D4AE" if dark else "#18815F",
        )

        rule(
            r"//[^\n]*",
            "#7591B1" if dark else "#7B8795",
        )

        self.rehighlight()

    def highlightBlock(self, text):
        for patron, formato in self.rules:
            coincidencias = patron.globalMatch(text)

            while coincidencias.hasNext():
                coincidencia = coincidencias.next()

                self.setFormat(
                    coincidencia.capturedStart(),
                    coincidencia.capturedLength(),
                    formato,
                )


class VentanaAST(QDialog):
    """Se muestra el arbol sintactico conservando su interfaz original."""

    def __init__(self, png_path: Path, dark: bool, parent=None):
        super().__init__(parent)

        ui = BASE_DIR / (
            "ventanaastazul.ui"
            if dark
            else "ventanaastblanco.ui"
        )

        if not ui.exists():
            raise FileNotFoundError(
                f"No existe el diseño Qt Designer: {ui.name}"
            )

        uic.loadUi(str(ui), self)

        self.png_path = Path(png_path)
        self.original = QPixmap(str(self.png_path))

        if self.original.isNull():
            raise RuntimeError(
                f"No se pudo leer el AST: {self.png_path}"
            )

        self.zoom = 1.0
        self.scrollAST.setWidgetResizable(False)

        self.imagen = QLabel()
        self.imagen.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.imagen.setStyleSheet(
            "background-color:white;border:0;"
        )

        self.scrollAST.setWidget(self.imagen)

        self.lblNombreAST.setText("Graphviz")
        self.lblNombreAST.setToolTip(self.png_path.name)

        self.btnZoomMenos.clicked.connect(self.alejar)
        self.btnZoomReset.clicked.connect(self.resetear)
        self.btnZoomMas.clicked.connect(self.acercar)
        self.btnAjustarVista.clicked.connect(self.ajustar)
        self.btnExportarAST.clicked.connect(self.exportar)
        self.btnCerrarAST.clicked.connect(self.close)

        self.resetear()
        QTimer.singleShot(0, self.ajustar)

    def aplicar_zoom(self):
        ancho = max(
            1,
            round(self.original.width() * self.zoom)
        )

        alto = max(
            1,
            round(self.original.height() * self.zoom)
        )

        imagen = self.original.scaled(
            ancho,
            alto,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.imagen.setPixmap(imagen)
        self.imagen.resize(imagen.size())

        self.lblASTAviso.setText(
            f"Zoom: {round(self.zoom * 100)}%"
        )

    def acercar(self):
        self.zoom = min(6.0, self.zoom * 1.25)
        self.aplicar_zoom()

    def alejar(self):
        self.zoom = max(0.03, self.zoom / 1.25)
        self.aplicar_zoom()

    def resetear(self):
        self.zoom = 1.0
        self.aplicar_zoom()

    def ajustar(self):
        viewport = self.scrollAST.viewport().size()

        self.zoom = max(
            0.03,
            min(
                (viewport.width() - 16)
                / max(1, self.original.width()),
                (viewport.height() - 16)
                / max(1, self.original.height()),
                1.0,
            ),
        )

        self.aplicar_zoom()

    def exportar(self):
        nombre = str(
            BASE_DIR / "AST_JARVIS_exportado.png"
        )

        archivo, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar árbol AST",
            nombre,
            "Imagen PNG (*.png)",
        )

        if not archivo:
            return

        destino = Path(archivo)

        try:
            if destino.resolve() != self.png_path.resolve():
                shutil.copy2(self.png_path, destino)

            QMessageBox.information(
                self,
                "Imagen exportada",
                f"AST guardado en:\n{destino}",
            )

        except OSError as error:
            QMessageBox.critical(
                self,
                "Error al exportar",
                str(error),
            )


class VentanaProblemas(QDialog):
    """Se muestran errores de las distintas fases del compilador."""

    def __init__(
        self,
        errores,
        fases,
        dark,
        parent=None,
    ):
        super().__init__(parent)

        ui = BASE_DIR / (
            "ventanaproblemasazul.ui"
            if dark
            else "ventanaproblemasblanco.ui"
        )

        if not ui.exists():
            raise FileNotFoundError(
                f"No existe el diseño de problemas: {ui.name}"
            )

        uic.loadUi(str(ui), self)

        self.errores = errores

        self.btnCerrarProblemas.clicked.connect(
            self.close
        )

        self.tblProblemas.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        self.tblProblemas.horizontalHeader().setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        self.tblProblemas.verticalHeader().hide()

        self.tblProblemas.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )

        self.tblProblemas.itemSelectionChanged.connect(
            self.mostrar_seleccion
        )

        if errores:
            self.lblEstadoProblemas.setText(
                "✕  Código con errores"
            )

            self.lblEstadoProblemas.setStyleSheet(
                "color:#EF4444;font-weight:bold;"
            )

            cantidad = len(errores)

            self.lblConteoProblemas.setText(
                f"{cantidad} error"
                + ("es" if cantidad != 1 else "")
            )

            self.lblConteoProblemas.setStyleSheet(
                "color:#EF4444;font-weight:bold;"
            )

        else:
            self.lblEstadoProblemas.setText(
                "✓  Sin problemas detectados"
            )

            self.lblEstadoProblemas.setStyleSheet(
                "color:#168455;font-weight:bold;"
            )

            self.lblConteoProblemas.setText(
                "0 errores"
            )

        controles = [
            ("lexico", self.lblLexicoProblemas),
            ("sintactico", self.lblSintacticoProblemas),
            ("semantico", self.lblSemanticoProblemas),
        ]

        for clave, widget in controles:
            estado = fases.get(clave, "pendiente")

            simbolo = {
                "ok": "✓",
                "error": "✕",
                "pendiente": "○",
            }.get(estado, "○")

            nombre = {
                "lexico": "Léxico",
                "sintactico": "Sintáctico",
                "semantico": "Semántico",
            }[clave]

            widget.setText(
                f"{simbolo}  {nombre}"
            )

            if estado == "error":
                color = "#E04444"

            elif estado == "ok":
                color = "#16A069"

            else:
                color = (
                    "#91A9C7"
                    if dark
                    else "#637C97"
                )

            widget.setStyleSheet(
                f"color:{color};font-weight:bold;"
            )

        self.tblProblemas.setRowCount(
            len(errores)
        )

        for fila, error in enumerate(errores):
            for columna, clave in enumerate(
                ("tipo", "linea", "mensaje")
            ):
                item = QTableWidgetItem(
                    str(error.get(clave, ""))
                )

                item.setForeground(
                    QColor(
                        "#E64A4A"
                        if dark
                        else "#B3261E"
                    )
                )

                self.tblProblemas.setItem(
                    fila,
                    columna,
                    item,
                )

        if errores:
            self.tblProblemas.selectRow(0)

        else:
            self.txtDetalleError.setPlainText(
                "El último análisis terminó sin errores."
            )

    def mostrar_seleccion(self):
        fila = self.tblProblemas.currentRow()

        if 0 <= fila < len(self.errores):
            error = self.errores[fila]

            mensaje = (
                f"{error.get('tipo', 'Error')}"
                f" · Línea: "
                f"{error.get('linea', 'No indicada')}"
                f"\n\n{error.get('mensaje', '')}"
            )

            self.txtDetalleError.setPlainText(
                mensaje
            )


def generar_ast_actual(arbol) -> Path:
    """Se utiliza el generador AST del compilador."""

    ruta = Path(
        generar_ast_principal(arbol)
    ).resolve()

    if not ruta.is_file():
        raise RuntimeError(
            "No se generó el archivo de imagen del AST."
        )

    if ruta.suffix.lower() != ".png":
        raise RuntimeError(
            "El AST generado no tiene formato PNG."
        )

    return ruta


class StarkLabApp(QMainWindow):
    """Ventana principal del compilador JARVIS."""

    def __init__(self):
        super().__init__()

        if not UI_FILE.is_file():
            raise FileNotFoundError(
                f"No se encontró el archivo .ui: {UI_FILE}"
            )

        uic.loadUi(str(UI_FILE), self)

        self.tema_oscuro = True
        self.archivo_actual: Path | None = None

        self.errores: list[dict] = []

        self.fases = {
            "lexico": "pendiente",
            "sintactico": "pendiente",
            "semantico": "pendiente",
        }

        self.estado_actual = "pendiente"
        self.error_linea = None
        self.ast_actual = None
        self.codigo_ast = None

        self.highlighter = ResaltadorJARVIS(
            self.txtCodigo.document(),
            True,
        )

        self._cargar_reactor()

        self.treeProyecto.expandAll()

        self.tblVariables.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        self.tblVariables.verticalHeader().setVisible(
            False
        )

        self.tblVariables.setShowGrid(False)

        self.txtBuscar.setPlaceholderText(
            "⌕  Buscar en el código...  Ctrl + F"
        )

        self.txtBuscar.setClearButtonEnabled(True)

        codigo_ejemplo = getattr(
            jarvis_parser,
            "codigo",
            "",
        ).strip()

        if codigo_ejemplo:
            self.txtCodigo.setPlainText(
                codigo_ejemplo
            )

            self.txtCodigo.document().setModified(
                False
            )

        self._configurar_pestanas()
        self._cargar_explorador()

        self.btnEjecutar.clicked.connect(
            self.ejecutar_mision
        )

        self.btnAnalizar.clicked.connect(
            self.analizar_codigo
        )

        self.btnLimpiar.clicked.connect(
            self.limpiar_paneles
        )

        self.btnNuevo.clicked.connect(
            self.nuevo_archivo
        )

        self.btnNuevaPestana.clicked.connect(
            self.nuevo_archivo
        )

        self.btnAbrir.clicked.connect(
            self.abrir_archivo
        )

        self.btnGuardar.clicked.connect(
            self.guardar_archivo
        )

        self.btnCopiar.clicked.connect(
            lambda: self.txtCodigo.copy()
        )

        self.btnPegar.clicked.connect(
            lambda: self.txtCodigo.paste()
        )

        self.btnBlanco.clicked.connect(
            lambda: self.cambiar_tema(False)
        )

        self.btnAzul.clicked.connect(
            lambda: self.cambiar_tema(True)
        )

        self.btnAST.clicked.connect(
            self.mostrar_ast
        )

        self.btnProblemas.clicked.connect(
            self.mostrar_problemas
        )

        self.btnBuscarPanel.clicked.connect(
            self.enfocar_busqueda
        )

        self.btnConsola.clicked.connect(
            self.txtConsola.setFocus
        )

        self.txtBuscar.textChanged.connect(
            self.resaltar_busqueda
        )

        self.txtBuscar.returnPressed.connect(
            self.buscar_siguiente
        )

        atajos = [
            ("Ctrl+F", self.enfocar_busqueda),
            ("Ctrl+S", self.guardar_archivo),
            ("Ctrl+O", self.abrir_archivo),
            ("Ctrl+N", self.nuevo_archivo),
        ]

        for combinacion, funcion in atajos:
            QShortcut(
                QKeySequence(combinacion),
                self,
            ).activated.connect(funcion)

        self.cambiar_tema(True)
        self.invalidar_analisis()
        self.actualizar_posicion()

    def _configurar_pestanas(self):
        """Se organizan los editores dentro de pestañas."""

        self.archivos_abiertos = []
        self.indice_pestana = -1
        self._actualizando_pestanas = False

        editor_inicial = self.txtCodigo

        self.stackCodigo = QStackedWidget(
            self.panelEditor
        )

        self.stackCodigo.setSizePolicy(
            editor_inicial.sizePolicy()
        )

        self.stackCodigo.setMinimumSize(
            editor_inicial.minimumSize()
        )

        self.layoutEditor.replaceWidget(
            editor_inicial,
            self.stackCodigo,
        )

        self.stackCodigo.addWidget(
            editor_inicial
        )

        self.pestanas = QTabBar(
            self.panelEditor
        )

        self.pestanas.setExpanding(False)
        self.pestanas.setTabsClosable(True)
        self.pestanas.setUsesScrollButtons(True)
        self.pestanas.setMovable(False)

        self.lblPestana.hide()

        self.layoutPestanas.removeWidget(
            self.lblPestana
        )

        self.layoutPestanas.insertWidget(
            0,
            self.pestanas,
        )

        self._registrar_editor(
            editor_inicial,
            "principal.jvs",
            None,
            self.highlighter,
        )

        self.pestanas.currentChanged.connect(
            self._activar_pestana
        )

        self.pestanas.tabCloseRequested.connect(
            self.cerrar_pestana
        )

        self._activar_pestana(0)

    def _registrar_editor(
        self,
        editor,
        nombre,
        ruta,
        resaltador=None,
    ):
        if resaltador is None:
            resaltador = ResaltadorJARVIS(
                editor.document(),
                self.tema_oscuro,
            )

        pestaña = {
            "editor": editor,
            "ruta": ruta,
            "nombre": nombre,
            "resaltador": resaltador,
        }

        self.archivos_abiertos.append(
            pestaña
        )

        self.pestanas.addTab(
            nombre
        )

        editor.textChanged.connect(
            lambda ed=editor: self._al_editar(ed)
        )

        editor.cursorPositionChanged.connect(
            lambda ed=editor: (
                self.actualizar_posicion()
                if ed is self.txtCodigo
                else None
            )
        )

        editor.document().modificationChanged.connect(
            lambda modificado, ed=editor:
            self._renombrar_pestana(ed)
        )

        self._renombrar_pestana(
            editor
        )

        return pestaña

    def _renombrar_pestana(self, editor):
        for indice, pestaña in enumerate(
            self.archivos_abiertos
        ):
            if pestaña["editor"] is editor:
                estrella = (
                    "*"
                    if editor.document().isModified()
                    else ""
                )

                self.pestanas.setTabText(
                    indice,
                    pestaña["nombre"] + estrella,
                )

                self.pestanas.setTabToolTip(
                    indice,
                    str(
                        pestaña["ruta"]
                        or "Archivo sin guardar"
                    ),
                )

                return

    def _activar_pestana(self, indice):
        if self._actualizando_pestanas:
            return

        if not 0 <= indice < len(self.archivos_abiertos):
            return

        pestaña = self.archivos_abiertos[
            indice
        ]

        self.indice_pestana = indice

        self.stackCodigo.setCurrentWidget(
            pestaña["editor"]
        )

        self.txtCodigo = pestaña["editor"]
        self.highlighter = pestaña["resaltador"]
        self.archivo_actual = pestaña["ruta"]

        self.txtBuscar.clear()
        self.limpiar_paneles()
        self.actualizar_posicion()

    def _al_editar(self, editor):
        self._renombrar_pestana(editor)

        if editor is self.txtCodigo:
            self.invalidar_analisis()

    def _estilo_pestanas(self):
        """Se conservan los colores originales de las pestañas."""

        if self.tema_oscuro:
            fondo = "#122845"
            texto = "#A9C7E7"
            activo = "#1D5280"
            borde = "#315B80"

        else:
            fondo = "#FFFFFF"
            texto = "#526F8F"
            activo = "#DCEEFF"
            borde = "#C4D9EA"

        self.pestanas.setStyleSheet(
            f"QTabBar {{background:transparent;}}"
            f"QTabBar::tab {{"
            f"background:{fondo};"
            f"color:{texto};"
            f"border:1px solid {borde};"
            f"border-radius:6px;"
            f"padding:6px 12px;"
            f"margin-right:4px;"
            f"min-width:75px;"
            f"}}"
            f"QTabBar::tab:selected {{"
            f"background:{activo};"
            f"font-weight:bold;"
            f"}}"
        )

    def _crear_nuevo_editor(
        self,
        nombre="nuevo.jvs",
        contenido="",
        ruta=None,
        solo_lectura=False,
    ):
        editor = QPlainTextEdit(
            self.stackCodigo
        )

        editor.setObjectName(
            "txtCodigo"
        )

        editor.setFont(
            self.txtCodigo.font()
        )

        editor.setLineWrapMode(
            self.txtCodigo.lineWrapMode()
        )

        editor.setTabStopDistance(
            self.txtCodigo.tabStopDistance()
        )

        editor.setReadOnly(
            solo_lectura
        )

        editor.setPlainText(
            contenido
        )

        editor.document().setModified(False)

        self.stackCodigo.addWidget(
            editor
        )

        self._actualizando_pestanas = True

        self._registrar_editor(
            editor,
            nombre,
            ruta,
        )

        indice = len(
            self.archivos_abiertos
        ) - 1

        self._actualizando_pestanas = False

        self.pestanas.setCurrentIndex(
            indice
        )

        self._activar_pestana(
            indice
        )

        return editor

    def _pedir_guardado(self, indice):
        pestaña = self.archivos_abiertos[indice]
        editor = pestaña["editor"]

        if not editor.document().isModified():
            return True

        dialogo = QMessageBox(self)

        dialogo.setWindowTitle(
            "Cambios sin guardar"
        )

        dialogo.setText(
            f"¿Deseas guardar los cambios de "
            f"{pestaña['nombre']}?"
        )

        dialogo.setIcon(
            QMessageBox.Icon.Question
        )

        dialogo.setStandardButtons(
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel
        )

        dialogo.button(
            QMessageBox.StandardButton.Save
        ).setText("Guardar")

        dialogo.button(
            QMessageBox.StandardButton.Discard
        ).setText("No guardar")

        dialogo.button(
            QMessageBox.StandardButton.Cancel
        ).setText("Cancelar")

        respuesta = dialogo.exec()

        if respuesta == QMessageBox.StandardButton.Cancel:
            return False

        if respuesta == QMessageBox.StandardButton.Save:
            self.pestanas.setCurrentIndex(indice)
            self._activar_pestana(indice)

            return self.guardar_archivo()

        return True

    def cerrar_pestana(self, indice):
        if not 0 <= indice < len(self.archivos_abiertos):
            return

        if not self._pedir_guardado(indice):
            return

        self._actualizando_pestanas = True

        pestaña = self.archivos_abiertos.pop(
            indice
        )

        self.pestanas.removeTab(
            indice
        )

        self.stackCodigo.removeWidget(
            pestaña["editor"]
        )

        pestaña["editor"].deleteLater()

        self._actualizando_pestanas = False

        if not self.archivos_abiertos:
            self.nuevo_archivo()

        else:
            nuevo_indice = min(
                indice,
                len(self.archivos_abiertos) - 1,
            )

            self.pestanas.setCurrentIndex(
                nuevo_indice
            )

            self._activar_pestana(
                nuevo_indice
            )

    def closeEvent(self, evento):
        for indice in range(
            len(self.archivos_abiertos)
        ):
            if not self._pedir_guardado(indice):
                evento.ignore()
                return

        evento.accept()

    def _cargar_explorador(self):
        """Se muestran los archivos reales del proyecto."""

        self.treeProyecto.clear()

        raiz = QTreeWidgetItem(
            self.treeProyecto,
            ["JARVIS"],
        )

        carpeta = QTreeWidgetItem(
            raiz,
            ["src"],
        )

        extensiones = {
            ".jvs",
            ".py",
        }

        archivos = sorted(
            (
                ruta
                for ruta in BASE_DIR.iterdir()
                if ruta.is_file()
                and ruta.suffix.lower() in extensiones
            ),
            key=lambda ruta: (
                ruta.suffix == ".py",
                ruta.name.lower(),
            ),
        )

        for ruta in archivos:
            item = QTreeWidgetItem(
                carpeta,
                [ruta.name],
            )

            item.setData(
                0,
                Qt.ItemDataRole.UserRole,
                str(ruta),
            )

        self.treeProyecto.expandAll()

        try:
            self.treeProyecto.itemDoubleClicked.disconnect(
                self._abrir_desde_arbol
            )

        except TypeError:
            pass

        self.treeProyecto.itemDoubleClicked.connect(
            self._abrir_desde_arbol
        )

    def _abrir_desde_arbol(
        self,
        item,
        columna,
    ):
        ruta = item.data(
            0,
            Qt.ItemDataRole.UserRole,
        )

        if ruta:
            self._abrir_ruta(
                Path(ruta)
            )

    def _abrir_ruta(self, ruta):
        ruta = ruta.resolve()

        if not ruta.is_file():
            QMessageBox.warning(
                self,
                "Archivo no encontrado",
                f"No se encuentra: {ruta}",
            )

            return

        for indice, pestaña in enumerate(
            self.archivos_abiertos
        ):
            actual = pestaña["ruta"]

            if actual and actual.resolve() == ruta:
                self.pestanas.setCurrentIndex(
                    indice
                )

                self._activar_pestana(
                    indice
                )

                return

        try:
            codigo = ruta.read_text(
                encoding="utf-8"
            )

        except (OSError, UnicodeError) as error:
            QMessageBox.critical(
                self,
                "Error al abrir",
                str(error),
            )
            return

        self._crear_nuevo_editor(
            ruta.name,
            codigo,
            ruta,
            ruta.suffix.lower() == ".py",
        )

        if ruta.suffix.lower() == ".py":
            self.statusBar().showMessage(
                "Archivo Python abierto en modo lectura",
                5000,
            )

    def _cargar_reactor(self):
        icono = (
            BASE_DIR
            / "assets"
            / "arc_reactor.png"
        )

        if icono.is_file():
            imagen = QPixmap(
                str(icono)
            )

            self.lblReactor.setPixmap(
                imagen.scaled(
                    53,
                    53,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

    def cambiar_tema(self, oscuro: bool):
        self.tema_oscuro = oscuro

        self.setStyleSheet(
            DARK_QSS
            if oscuro
            else LIGHT_QSS
        )

        for pestaña in self.archivos_abiertos:
            pestaña["resaltador"].set_dark(
                oscuro
            )

        self._estilo_pestanas()
        self._colorear_estado()

    def _colorear_estado(self):
        """Se actualizan los indicadores del analisis."""

        if self.estado_actual == "error":
            color = (
                "#FF6464"
                if self.tema_oscuro
                else "#C62828"
            )

            fondo = (
                "#47222E"
                if self.tema_oscuro
                else "#FFF0F0"
            )

            borde = "#DB5656"

        elif self.estado_actual == "valido":
            color = (
                "#5FDEAA"
                if self.tema_oscuro
                else "#117F52"
            )

            fondo = (
                "#173D39"
                if self.tema_oscuro
                else "#E8F6ED"
            )

            borde = "#409B7F"

        else:
            color = (
                "#B3C5DE"
                if self.tema_oscuro
                else "#627C98"
            )

            fondo = (
                "#1B354F"
                if self.tema_oscuro
                else "#EDF3F8"
            )

            borde = (
                "#55738E"
                if self.tema_oscuro
                else "#D8E2EA"
            )

        for widget in (
            self.lblEstadoAnalisis,
            self.lblErrores,
        ):
            widget.setStyleSheet(
                f"color:{color};font-weight:700;"
            )

        detalle_color = (
            color
            if self.estado_actual == "error"
            else (
                "#9DB7D2"
                if self.tema_oscuro
                else "#69819A"
            )
        )

        self.lblAnalisisDetalle.setStyleSheet(
            f"color:{detalle_color};"
        )

        colores = {
            "ok": (
                "#57DCA6"
                if self.tema_oscuro
                else "#14885B",
                "#193E35"
                if self.tema_oscuro
                else "#E6F7ED",
            ),
            "error": (
                "#FF6262"
                if self.tema_oscuro
                else "#C62828",
                "#47222E"
                if self.tema_oscuro
                else "#FFE9E9",
            ),
            "pendiente": (
                "#A7BBD4"
                if self.tema_oscuro
                else "#637D99",
                "#1B354F"
                if self.tema_oscuro
                else "#EDF2F9",
            ),
        }

        controles = [
            ("lexico", self.lblLexico),
            ("sintactico", self.lblSintactico),
            ("semantico", self.lblSemantico),
        ]

        for clave, widget in controles:
            tinta, fondo_fase = colores[
                self.fases.get(clave, "pendiente")
            ]

            widget.setStyleSheet(
                f"color:{tinta};"
                f"background:{fondo_fase};"
                f"border-radius:6px;"
                f"padding:8px;"
                f"font-weight:600;"
            )

        if self.estado_actual == "error":
            self.txtConsola.setStyleSheet(
                f"QPlainTextEdit {{"
                f"color:{color};"
                f"background:{fondo};"
                f"border:2px solid {borde};"
                f"border-radius:8px;"
                f"padding:9px;"
                f"font-family:Consolas;"
                f"font-size:13px;"
                f"}}"
            )

        else:
            self.txtConsola.setStyleSheet("")

        self.lblLineaEstado.setStyleSheet(
            f"color:{color};"
        )

    def actualizar_posicion(self):
        cursor = self.txtCodigo.textCursor()

        linea = cursor.blockNumber() + 1
        columna = cursor.positionInBlock() + 1

        self.lblPosicion.setText(
            f"UTF-8  ·  Ln {linea}, Col {columna}"
        )

    def invalidar_analisis(self):
        self.ast_actual = None
        self.codigo_ast = None
        self.error_linea = None
        self.errores = []

        self.fases = {
            "lexico": "pendiente",
            "sintactico": "pendiente",
            "semantico": "pendiente",
        }

        self.estado_actual = "pendiente"

        self.lblEstadoAnalisis.setText(
            "○  Código sin analizar"
        )

        self.lblAnalisisDetalle.setText(
            "Pulsa Analizar código para comprobarlo."
        )

        self.lblLexico.setText(
            "○  Léxico"
        )

        self.lblSintactico.setText(
            "○  Sintaxis"
        )

        self.lblSemantico.setText(
            "○  Semántica"
        )

        self.lblErrores.setText("—")

        self.lblProblemasCount.setText(
            "Problemas (—)"
        )

        self.lblLineaEstado.setText(
            "○  Sin analizar"
        )

        if hasattr(self, "txtConsola"):
            self.txtConsola.clear()

        self._colorear_estado()

        if hasattr(self, "txtBuscar"):
            self.resaltar_busqueda()

    def enfocar_busqueda(self):
        self.txtBuscar.setFocus()
        self.txtBuscar.selectAll()

    def resaltar_busqueda(self):
        termino = self.txtBuscar.text()
        documento = self.txtCodigo.document()

        selecciones = []

        # Se destaca la linea donde ocurre un error.
        if (
            self.error_linea
            and 1 <= self.error_linea <= documento.blockCount()
        ):
            cursor = QTextCursor(
                documento.findBlockByNumber(
                    self.error_linea - 1
                )
            )

            seleccion = QTextEdit.ExtraSelection()
            seleccion.cursor = cursor

            seleccion.format.setBackground(
                QColor(
                    "#5A2435"
                    if self.tema_oscuro
                    else "#FFDBDB"
                )
            )

            seleccion.format.setProperty(
                QTextFormat.Property.FullWidthSelection,
                True,
            )

            selecciones.append(
                seleccion
            )

        if termino:
            formato = QTextCharFormat()

            formato.setBackground(
                QColor("#F5C84D")
            )

            formato.setForeground(
                QColor("#0C2039")
            )

            posicion = 0

            for _ in range(350):
                cursor = documento.find(
                    termino,
                    posicion,
                )

                if cursor.isNull():
                    break

                seleccion = QTextEdit.ExtraSelection()
                seleccion.cursor = cursor
                seleccion.format = formato

                selecciones.append(
                    seleccion
                )

                posicion = cursor.selectionEnd()

        self.txtCodigo.setExtraSelections(
            selecciones
        )

    def buscar_siguiente(self):
        termino = self.txtBuscar.text()

        if termino and not self.txtCodigo.find(termino):
            cursor = self.txtCodigo.textCursor()

            cursor.movePosition(
                QTextCursor.MoveOperation.Start
            )

            self.txtCodigo.setTextCursor(cursor)
            self.txtCodigo.find(termino)

    def _parsear(self):
        """Se realizan los tres analisis del compilador."""

        codigo = self.txtCodigo.toPlainText()

        if not codigo.strip():
            raise SyntaxError(
                "Escribe código JARVIS antes de analizar."
            )

        lexer.lineno = 1
        salida = io.StringIO()

        try:
            with contextlib.redirect_stdout(salida):
                arbol = jarvis_parser.parser.parse(
                    codigo,
                    lexer=lexer,
                )

        except Exception as error:
            texto = salida.getvalue()

            if re.search(
                r"error\s+l[eé]xico|"
                r"car[aá]cter\s+(?:ilegal|inv[aá]lido)",
                texto,
                re.IGNORECASE,
            ):
                raise ErrorLexicoJARVIS(
                    texto.strip()
                ) from error

            raise

        texto = salida.getvalue()

        if re.search(
            r"error\s+l[eé]xico|"
            r"car[aá]cter\s+(?:ilegal|inv[aá]lido)",
            texto,
            re.IGNORECASE,
        ):
            raise ErrorLexicoJARVIS(
                texto.strip()
            )

        if re.search(
            r"error\s+sint[aá]ctico",
            texto,
            re.IGNORECASE,
        ):
            raise SyntaxError(
                texto.strip()
            )

        if arbol is None:
            raise SyntaxError(
                "No se pudo construir el AST. "
                "Revisa la sintaxis."
            )

        with contextlib.redirect_stdout(salida):
            analizar_programa(arbol)

        return arbol, salida.getvalue()

    def _tipo_error(self, error, texto_salida=""):
        texto = f"{texto_salida} {error}"

        if isinstance(
            error,
            ErrorLexicoJARVIS,
        ) or re.search(
            r"error\s+l[eé]xico|"
            r"car[aá]cter\s+ilegal",
            texto,
            re.IGNORECASE,
        ):
            return "Léxico"

        if isinstance(
            error,
            ErrorSemantico,
        ) or re.search(
            r"sem[aá]ntic",
            texto,
            re.IGNORECASE,
        ):
            return "Semántico"

        if isinstance(
            error,
            SyntaxError,
        ) or re.search(
            r"sint[aá]ct",
            texto,
            re.IGNORECASE,
        ):
            return "Sintáctico"

        return "Análisis"

    def _linea_error(self, mensaje):
        coincidencia = re.search(
            r"(?:l[ií]nea|line)\s*[:#-]?\s*(\d+)",
            mensaje,
            re.IGNORECASE,
        )

        if coincidencia:
            return int(
                coincidencia.group(1)
            )

        return None

    def _linea_semantica(self, mensaje):
        coincidencia = re.search(
            r"variable ['\"]([^'\"]+)['\"]",
            mensaje,
            re.IGNORECASE,
        )

        if not coincidencia:
            return None

        nombre = coincidencia.group(1)
        coincidencias = []

        lineas = self.txtCodigo.toPlainText().splitlines()

        for numero, linea in enumerate(lineas, 1):
            patron = (
                r"\b"
                + re.escape(nombre)
                + r"\b\s*(?::|=)"
            )

            if re.search(patron, linea):
                coincidencias.append(numero)

        if len(coincidencias) == 1:
            return coincidencias[0]

        return None

    def _estado(
        self,
        correcto: bool,
        mensaje="",
        tipo="Sintáctico",
    ):
        self.estado_actual = (
            "valido"
            if correcto
            else "error"
        )

        if correcto:
            self.lblEstadoAnalisis.setText(
                "✓  Código válido"
            )

            self.lblAnalisisDetalle.setText(
                "Análisis léxico, sintáctico "
                "y semántico correcto."
            )

            self.fases = {
                "lexico": "ok",
                "sintactico": "ok",
                "semantico": "ok",
            }

            self.lblLexico.setText("✓  Léxico")
            self.lblSintactico.setText("✓  Sintaxis")
            self.lblSemantico.setText("✓  Semántica")

            self.lblErrores.setText(
                "0 errores"
            )

            self.lblProblemasCount.setText(
                "Problemas (0)"
            )

            self.lblLineaEstado.setText(
                "●  Análisis correcto"
            )

            self.error_linea = None
            self.errores = []

        else:
            if tipo == "Ejecución":
                titulo = "✕  Error de ejecución"

            else:
                titulo = "✕  Código con errores"

            self.lblEstadoAnalisis.setText(
                titulo
            )

            self.lblAnalisisDetalle.setText(
                f"Error {tipo.lower()}. "
                "Haz clic en «Ver problemas»."
            )

            fases_por_error = {
                "Léxico": {
                    "lexico": "error",
                    "sintactico": "pendiente",
                    "semantico": "pendiente",
                },
                "Sintáctico": {
                    "lexico": "ok",
                    "sintactico": "error",
                    "semantico": "pendiente",
                },
                "Semántico": {
                    "lexico": "ok",
                    "sintactico": "ok",
                    "semantico": "error",
                },
                "Ejecución": {
                    "lexico": "ok",
                    "sintactico": "ok",
                    "semantico": "ok",
                },
                "Análisis": {
                    "lexico": "pendiente",
                    "sintactico": "pendiente",
                    "semantico": "pendiente",
                },
            }

            self.fases = fases_por_error.get(
                tipo,
                fases_por_error["Análisis"],
            )

            controles = [
                (
                    "lexico",
                    self.lblLexico,
                    "Léxico",
                ),
                (
                    "sintactico",
                    self.lblSintactico,
                    "Sintaxis",
                ),
                (
                    "semantico",
                    self.lblSemantico,
                    "Semántica",
                ),
            ]

            for clave, widget, nombre in controles:
                estado = self.fases[clave]

                simbolo = {
                    "ok": "✓",
                    "error": "✕",
                    "pendiente": "○",
                }[estado]

                widget.setText(
                    f"{simbolo}  {nombre}"
                )

            if tipo == "Léxico":
                lineas = [
                    linea.strip()
                    for linea in mensaje.splitlines()
                    if re.search(
                        r"error\s+l[eé]xico",
                        linea,
                        re.IGNORECASE,
                    )
                ]

            else:
                lineas = []

            self.errores = []

            for detalle in (
                lineas or [mensaje]
            ):
                numero = self._linea_error(
                    detalle
                )

                if numero is None and tipo == "Semántico":
                    numero = self._linea_semantica(
                        detalle
                    )

                self.errores.append(
                    {
                        "tipo": tipo,
                        "linea": (
                            numero
                            if numero is not None
                            else "No indicada"
                        ),
                        "mensaje": detalle,
                    }
                )

            self.error_linea = self.errores[0]["linea"]

            if not isinstance(
                self.error_linea,
                int,
            ):
                self.error_linea = None

            cantidad = len(
                self.errores
            )

            self.lblErrores.setText(
                f"{cantidad} error"
                + ("es" if cantidad != 1 else "")
            )

            self.lblProblemasCount.setText(
                f"Problemas ({cantidad})"
            )

            self.lblLineaEstado.setText(
                "✕  Revisa los errores"
            )

        self._colorear_estado()
        self.resaltar_busqueda()

    def analizar_codigo(self):
        """Se analiza el contenido de la pestaña activa."""

        if (
            self.archivo_actual
            and self.archivo_actual.suffix.lower() == ".py"
        ):
            QMessageBox.information(
                self,
                "Archivo Python",
                "Solo se pueden analizar programas "
                "escritos en JARVIS.",
            )

            return None

        try:
            arbol, advertencias = self._parsear()

            self.ast_actual = arbol
            self.codigo_ast = (
                self.txtCodigo.toPlainText()
            )

            self._estado(True)

            mensaje = (
                "✓ Análisis léxico, sintáctico "
                "y semántico correcto."
            )

            if advertencias.strip():
                mensaje += (
                    "\n" + advertencias.strip()
                )

            self.txtConsola.setPlainText(
                mensaje
            )

            return arbol

        except Exception as error:
            tipo = self._tipo_error(
                error
            )

            self._estado(
                False,
                str(error),
                tipo,
            )

            self.txtConsola.setPlainText(
                f"✕  ERROR {tipo.upper()} "
                f"DE JARVIS\n\n"
                f"{error}\n\n"
                "Usa «Ver problemas» para "
                "consultar los detalles."
            )

            self.ast_actual = None
            self.codigo_ast = None

            return None

    def _pedir_entrada(self, mensaje: str) -> str:
        """Se solicita un dato desde una ventana de PyQt6."""

        respuesta, aceptado = QInputDialog.getText(
            self,
            "J.A.R.V.I.S | Entrada",
            mensaje or "Introduce un valor:",
        )

        if not aceptado:
            raise ErrorEjecucionJARVIS(
                "La entrada fue cancelada por el usuario."
            )

        return respuesta

    def ejecutar_mision(self):
        """Se analiza y se ejecuta el programa JARVIS."""

        arbol = self.analizar_codigo()

        if arbol is None:
            return

        salida = io.StringIO()

        ejecutor = EjecutorJARVIS(
            proveedor_entrada=self._pedir_entrada
        )

        try:
            with contextlib.redirect_stdout(salida):
                ejecutor.ejecutar_programa(arbol)

        except Exception as error:
            self._estado(
                False,
                str(error),
                "Ejecución",
            )

            self.txtConsola.setPlainText(
                "✕  ERROR DE EJECUCIÓN JARVIS\n\n"
                f"{error}\n\n"
                + salida.getvalue()
            )

        else:
            texto = salida.getvalue().strip()

            if not texto:
                texto = (
                    "La misión terminó sin "
                    "texto de salida."
                )

            self.txtConsola.setPlainText(
                texto
            )

        # Se muestran las variables del ejecutor.
        elementos = list(
            ejecutor.variables.items()
        )

        self.tblVariables.setRowCount(
            len(elementos)
        )

        for fila, (nombre, valor) in enumerate(
            elementos
        ):
            self.tblVariables.setItem(
                fila,
                0,
                QTableWidgetItem(str(nombre)),
            )

            self.tblVariables.setItem(
                fila,
                1,
                QTableWidgetItem(
                    tipo_jarvis(nombre, valor)
                ),
            )

            self.tblVariables.setItem(
                fila,
                2,
                QTableWidgetItem(str(valor)),
            )

        self.lblCantidadVariables.setText(
            f"{len(elementos)} activas"
        )

        energia = ejecutor.variables.get(
            "energia"
        )

        if energia is not None:
            self.lblEnergiaFinal.setText(
                f"ENERGÍA FINAL: {energia} / 100"
            )

        else:
            self.lblEnergiaFinal.setText(
                "ENERGÍA FINAL: —"
            )

        self.guardar_registro(
            self.txtConsola.toPlainText(),
            ejecutor,
        )

    def guardar_registro(
        self,
        salida: str,
        ejecutor,
    ):
        """Se almacena el resultado de cada ejecucion."""

        try:
            with REGISTROS_FILE.open(
                "a",
                encoding="utf-8",
            ) as archivo:
                fecha = datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

                archivo.write(
                    f"========== {fecha} ==========\n"
                )

                archivo.write(
                    self.lblEstadoAnalisis.text()
                    + "\n"
                )

                for nombre, valor in ejecutor.variables.items():
                    archivo.write(
                        f"{nombre} "
                        f"({tipo_jarvis(nombre, valor)}): "
                        f"{valor}\n"
                    )

                archivo.write(
                    "SALIDA:\n"
                    + salida
                    + "\n\n"
                )

        except OSError as error:
            self.statusBar().showMessage(
                "No se pudo escribir registros.txt: "
                f"{error}",
                8000,
            )

    def mostrar_problemas(self):
        ventana = VentanaProblemas(
            self.errores,
            self.fases,
            self.tema_oscuro,
            self,
        )

        ventana.exec()

    def mostrar_ast(self):
        """Se abre el AST correspondiente al codigo analizado."""

        codigo = self.txtCodigo.toPlainText()

        if (
            self.ast_actual is not None
            and self.codigo_ast == codigo
        ):
            arbol = self.ast_actual

        else:
            arbol = self.analizar_codigo()

        if arbol is None:
            QMessageBox.warning(
                self,
                "AST no disponible",
                "El código tiene errores. "
                "Corrígelos antes de ver el árbol.",
            )

            return

        try:
            ruta = generar_ast_actual(
                arbol
            )

            ventana = VentanaAST(
                ruta,
                self.tema_oscuro,
                self,
            )

            ventana.exec()

        except Exception as error:
            QMessageBox.critical(
                self,
                "No se pudo generar el AST",
                "Error al generar o abrir "
                f"la imagen real:\n{error}",
            )

    def limpiar_paneles(self):
        """Se limpian la consola y los indicadores."""

        self.txtConsola.clear()
        self.tblVariables.setRowCount(0)

        self.lblCantidadVariables.setText(
            "0 activas"
        )

        self.lblEnergiaFinal.setText(
            "ENERGÍA FINAL:  —"
        )

        self.invalidar_analisis()

    def nuevo_archivo(self):
        """Se agrega una pestaña para un programa nuevo."""

        nombres = {
            pestaña["nombre"]
            for pestaña in self.archivos_abiertos
        }

        nombre = "nuevo.jvs"
        numero = 2

        while nombre in nombres:
            nombre = f"nuevo_{numero}.jvs"
            numero += 1

        self._crear_nuevo_editor(
            nombre
        )

    def abrir_archivo(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir programa JARVIS",
            str(BASE_DIR),
            "Programas JARVIS (*.jvs);;"
            "Archivos Python (*.py)",
        )

        if ruta:
            self._abrir_ruta(
                Path(ruta)
            )

    def guardar_archivo(self):
        """Se guarda el programa activo como archivo JVS."""

        pestaña = self.archivos_abiertos[
            self.indice_pestana
        ]

        editor = pestaña["editor"]

        if editor.isReadOnly():
            QMessageBox.information(
                self,
                "Solo lectura",
                "Este archivo se está mostrando "
                "solo para consulta.",
            )

            return False

        ruta = pestaña["ruta"]

        if ruta is None:
            nombre, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar código JARVIS",
                str(BASE_DIR / "principal.jvs"),
                "Programas JARVIS (*.jvs)",
            )

            if not nombre:
                return False

            ruta = Path(nombre)

            if ruta.suffix.lower() != ".jvs":
                ruta = ruta.with_suffix(".jvs")

        try:
            ruta.write_text(
                editor.toPlainText(),
                encoding="utf-8",
            )

        except OSError as error:
            QMessageBox.critical(
                self,
                "Error al guardar",
                str(error),
            )

            return False

        pestaña["ruta"] = ruta
        pestaña["nombre"] = ruta.name

        self.archivo_actual = ruta

        editor.document().setModified(
            False
        )

        self._renombrar_pestana(
            editor
        )

        self.statusBar().showMessage(
            f"Guardado: {ruta.name}",
            4000,
        )

        self._cargar_explorador()

        return True


def main():
    app = QApplication(sys.argv)

    ventana = StarkLabApp()
    ventana.show()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":
    main()

