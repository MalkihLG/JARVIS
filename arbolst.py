
# ==============================================
# JARVIS - VISUALIZADOR DEL AST
# Graphviz + Python
# ==============================================

from pathlib import Path
from graphviz import Digraph

from lexer import lexer
from parser import parser, codigo


# CREAR EL ARBOL GRAFICO

def generar_ast(arbol):

    grafico = Digraph(
        "AST_JARVIS",
        format="png"
    )

    # Configuracion visual
    grafico.attr(rankdir="TB")
    grafico.attr(
        "node",
        shape="box",
        style="rounded,filled",
        fillcolor="#DDEFFF",
        color="#2474A6",
        fontname="Arial"
    )

    contador = 0

    # CREAR NODOS
    def nodo(etiqueta):
        nonlocal contador

        contador += 1
        identificador = str(contador)

        grafico.node(identificador, etiqueta)

        return identificador

    # DIBUJAR EXPRESIONES
    def expresion(valor):

        if isinstance(valor, dict):

            tipo = valor.get("tipo")

            if tipo in ("operacion", "comparacion"):

                actual = nodo(
                    f"{tipo.capitalize()}: "
                    f"{valor['operador']}"
                )

                izquierda = expresion(
                    valor["izquierda"]
                )

                derecha = expresion(
                    valor["derecha"]
                )

                grafico.edge(
                    actual, izquierda, label="izq"
                )

                grafico.edge(
                    actual, derecha, label="der"
                )

                return actual

        return nodo(f"Valor: {valor}")

    # DIBUJAR INSTRUCCIONES
    def instruccion(datos):

        tipo = datos["tipo"]

        # Variables
        if tipo == "variable":

            actual = nodo(
                f"Variable: {datos['nombre']}\n"
                f"Tipo: {datos['dato']}"
            )

            valor = expresion(datos["valor"])

            grafico.edge(
                actual, valor, label="valor"
            )

            return actual

        # Imprimir
        if tipo == "imprimir":

            actual = nodo("Imprimir")

            mensaje = expresion(
                datos["mensaje"]
            )

            grafico.edge(actual, mensaje)

            return actual

        # Condiciones SI / SINO
        if tipo == "si":

            actual = nodo("Condicion SI")

            condicion = expresion(
                datos["condicion"]
            )

            grafico.edge(
                actual, condicion,
                label="condicion"
            )

            # Bloque SI
            bloque_si = nodo("Bloque SI")
            grafico.edge(actual, bloque_si)

            for elemento in datos["instrucciones_si"]:

                hijo = instruccion(elemento)

                grafico.edge(bloque_si, hijo)

            # Bloque SINO
            if datos["instrucciones_sino"]:

                bloque_sino = nodo("Bloque SINO")

                grafico.edge(actual, bloque_sino)

                for elemento in datos["instrucciones_sino"]:

                    hijo = instruccion(elemento)

                    grafico.edge(bloque_sino, hijo)

            return actual

        return nodo(f"Instruccion: {tipo}")

    # RAIZ DEL AST
    raiz = nodo(
        f"Sistema: {arbol['nombre']}"
    )

    # MISION PRINCIPAL
    mision = arbol["mision"]

    nodo_mision = nodo(
        f"Mision: {mision['nombre']}"
    )

    grafico.edge(raiz, nodo_mision)

    # AGREGAR INSTRUCCIONES
    for elemento in mision["instrucciones"]:

        hijo = instruccion(elemento)

        grafico.edge(nodo_mision, hijo)

    # GUARDAR EL ARCHIVO
    carpeta = Path(__file__).resolve().parent / "arboles"

    carpeta.mkdir(
        parents=True,
        exist_ok=True
    )

    ruta = grafico.render(
        filename="AST_JARVIS",
        directory=str(carpeta),
        cleanup=True
    )

    return ruta


# PROGRAMA PRINCIPAL

if __name__ == "__main__":

    try:

        lexer.lineno = 1

        resultado = parser.parse(
            codigo,
            lexer=lexer
        )

        if resultado is None:
            raise SyntaxError(
                "No se pudo construir el AST"
            )

        ruta = generar_ast(resultado)

        print("========== JARVIS ==========")
        print("Analisis sintactico correcto")
        print("AST generado correctamente")
        print("Archivo guardado en:")
        print(ruta)

    except Exception as error:

        print("Error al generar AST:")
        print(error)
