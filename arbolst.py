
# ==============================================
# JARVIS - VISUALIZADOR DEL AST
# Graphviz + Python
# ==============================================

from pathlib import Path
from graphviz import Digraph

from lexer import lexer
from parser import parser, codigo


# ==============================================
# 1. CREAR EL ARBOL GRAFICO
# ==============================================

def generar_ast(arbol):

    grafico = Digraph(
        "AST_JARVIS",
        format="png"
    )

    # CONFIGURACION VISUAL
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

    # ==========================================
    # 2. CREAR NODOS
    # ==========================================

    def nodo(etiqueta):

        nonlocal contador

        contador += 1

        identificador = str(contador)

        grafico.node(
            identificador,
            etiqueta
        )

        return identificador

    # ==========================================
    # 3. DIBUJAR EXPRESIONES
    # ==========================================

    def expresion(valor):

        # COMPROBAR SI ES UNA EXPRESION
        if isinstance(valor, dict):

            tipo = valor.get("tipo")

            # ----------------------------------
            # IDENTIFICADORES DE VARIABLES
            # ----------------------------------

            if tipo == "identificador":

                nombre = valor["nombre"]

                return nodo(
                    f"Identificador: {nombre}"
                )

            # ----------------------------------
            # OPERACIONES Y COMPARACIONES
            # ----------------------------------

            if tipo in ("operacion", "comparacion"):

                actual = nodo(
                    f"{tipo.capitalize()}: "
                    f"{valor['operador']}"
                )

                # OPERANDO IZQUIERDO
                izquierda = expresion(
                    valor["izquierda"]
                )

                # OPERANDO DERECHO
                derecha = expresion(
                    valor["derecha"]
                )

                grafico.edge(
                    actual,
                    izquierda,
                    label="izq"
                )

                grafico.edge(
                    actual,
                    derecha,
                    label="der"
                )

                return actual

            # EXPRESION DESCONOCIDA
            return nodo(
                f"Expresion: {tipo}"
            )

        # ----------------------------------
        # VALORES LITERALES
        # ----------------------------------

        return nodo(
            f"Valor: {valor}"
        )

    # ==========================================
    # 4. DIBUJAR INSTRUCCIONES
    # ==========================================

    def instruccion(datos):

        tipo = datos["tipo"]

        # ----------------------------------
        # DECLARACION DE VARIABLES
        # ----------------------------------

        if tipo == "variable":

            actual = nodo(
                f"Variable: {datos['nombre']}\n"
                f"Tipo: {datos['dato']}"
            )

            valor = expresion(
                datos["valor"]
            )

            grafico.edge(
                actual,
                valor,
                label="valor"
            )

            return actual

        # ----------------------------------
        # ASIGNACIONES DE VARIABLES
        # ----------------------------------

        if tipo == "asignacion":

            actual = nodo(
                f"Asignacion: {datos['nombre']} "
                f"{datos['operador']}"
            )

            valor = expresion(
                datos["valor"]
            )

            grafico.edge(
                actual,
                valor,
                label="valor"
            )

            return actual

        # ----------------------------------
        # LLAMADAS A FUNCIONES
        # ----------------------------------

        if tipo == "llamada":

            actual = nodo(
                f"Llamada: {datos['nombre']}()"
            )

            argumentos = datos.get(
                "argumentos",
                []
            )

            for indice, argumento in enumerate(
                argumentos,
                start=1
            ):

                hijo = expresion(
                    argumento
                )

                grafico.edge(
                    actual,
                    hijo,
                    label=f"arg {indice}"
                )

            return actual

        # ----------------------------------
        # INSTRUCCION IMPRIMIR
        # ----------------------------------

        if tipo == "imprimir":

            actual = nodo(
                "Imprimir"
            )

            mensaje = expresion(
                datos["mensaje"]
            )

            grafico.edge(
                actual,
                mensaje,
                label="mensaje"
            )

            return actual

        # ----------------------------------
        # CICLO REPETIR
        # ----------------------------------

        if tipo == "repetir":

            actual = nodo(
                "Ciclo REPETIR"
            )

            # CANTIDAD DE REPETICIONES
            cantidad = expresion(
                datos["cantidad"]
            )

            grafico.edge(
                actual,
                cantidad,
                label="veces"
            )

            # CUERPO DEL CICLO
            bloque = nodo(
                "Bloque REPETIR"
            )

            grafico.edge(
                actual,
                bloque
            )

            for elemento in datos["instrucciones"]:

                hijo = instruccion(
                    elemento
                )

                grafico.edge(
                    bloque,
                    hijo
                )

            return actual

        # ----------------------------------
        # CICLO MIENTRAS
        # ----------------------------------

        if tipo == "mientras":

            actual = nodo(
                "Ciclo MIENTRAS"
            )

            # CONDICION DEL CICLO
            condicion = expresion(
                datos["condicion"]
            )

            grafico.edge(
                actual,
                condicion,
                label="condicion"
            )

            # CUERPO DEL CICLO
            bloque = nodo(
                "Bloque MIENTRAS"
            )

            grafico.edge(
                actual,
                bloque
            )

            for elemento in datos["instrucciones"]:

                hijo = instruccion(
                    elemento
                )

                grafico.edge(
                    bloque,
                    hijo
                )

            return actual

        # ----------------------------------
        # CONDICIONES SI / SINO
        # ----------------------------------

        if tipo == "si":

            actual = nodo(
                "Condicion SI"
            )

            # CONDICION
            condicion = expresion(
                datos["condicion"]
            )

            grafico.edge(
                actual,
                condicion,
                label="condicion"
            )

            # BLOQUE SI
            bloque_si = nodo(
                "Bloque SI"
            )

            grafico.edge(
                actual,
                bloque_si
            )

            for elemento in datos["instrucciones_si"]:

                hijo = instruccion(
                    elemento
                )

                grafico.edge(
                    bloque_si,
                    hijo
                )

            # BLOQUE SINO
            if datos["instrucciones_sino"]:

                bloque_sino = nodo(
                    "Bloque SINO"
                )

                grafico.edge(
                    actual,
                    bloque_sino
                )

                for elemento in datos["instrucciones_sino"]:

                    hijo = instruccion(
                        elemento
                    )

                    grafico.edge(
                        bloque_sino,
                        hijo
                    )

            return actual

        # ----------------------------------
        # OTRAS INSTRUCCIONES
        # ----------------------------------

        return nodo(
            f"Instruccion: {tipo}"
        )

    # ==========================================
    # 5. CREAR RAIZ DEL AST
    # ==========================================

    raiz = nodo(
        f"Sistema: {arbol['nombre']}"
    )

    # ==========================================
    # 6. FUNCIONES DECLARADAS
    # ==========================================

    for accion in arbol.get("acciones", []):

        # NODO DE LA ACCION
        nodo_accion = nodo(
            f"Accion: {accion['nombre']}"
        )

        grafico.edge(
            raiz,
            nodo_accion
        )

        # ----------------------------------
        # PARAMETROS DE LA FUNCION
        # ----------------------------------

        for parametro in accion.get("parametros", []):

            nodo_parametro = nodo(
                f"Parametro: {parametro['nombre']}\n"
                f"Tipo: {parametro['tipo']}"
            )

            grafico.edge(
                nodo_accion,
                nodo_parametro,
                label="parametro"
            )

        # ----------------------------------
        # CUERPO DE LA FUNCION
        # ----------------------------------

        bloque = nodo(
            "Cuerpo de la accion"
        )

        grafico.edge(
            nodo_accion,
            bloque
        )

        for elemento in accion["instrucciones"]:

            hijo = instruccion(
                elemento
            )

            grafico.edge(
                bloque,
                hijo
            )

    # ==========================================
    # 7. MISION PRINCIPAL
    # ==========================================

    mision = arbol["mision"]

    nodo_mision = nodo(
        f"Mision: {mision['nombre']}"
    )

    grafico.edge(
        raiz,
        nodo_mision
    )

    # ----------------------------------
    # INSTRUCCIONES DE LA MISION
    # ----------------------------------

    for elemento in mision["instrucciones"]:

        hijo = instruccion(
            elemento
        )

        grafico.edge(
            nodo_mision,
            hijo
        )

    # ==========================================
    # 8. GUARDAR EL ARCHIVO
    # ==========================================

    carpeta = (
        Path(__file__).resolve().parent
        / "arboles"
    )

    carpeta.mkdir(
        parents=True,
        exist_ok=True
    )

    ruta = grafico.render(
        filename="AST_JARVIS_NUEVO",
        directory=str(carpeta),
        cleanup=True
    )

    return ruta


# ==============================================
# 9. PROGRAMA PRINCIPAL
# ==============================================

if __name__ == "__main__":

    try:

        # REINICIAR NUMERO DE LINEA
        lexer.lineno = 1

        # ANALISIS SINTACTICO
        resultado = parser.parse(
            codigo,
            lexer=lexer
        )

        # COMPROBAR EL ARBOL
        if resultado is None:

            raise SyntaxError(
                "No se pudo construir el AST"
            )

        # GENERAR IMAGEN
        ruta = generar_ast(
            resultado
        )

        # MOSTRAR RESULTADOS
        print("========== JARVIS ==========")
        print("Analisis sintactico correcto")
        print("AST generado correctamente")
        print("Archivo guardado en:")
        print(ruta)

    except Exception as error:

        print("========== ERROR JARVIS ==========")
        print("Error al generar AST:")
        print(error)
