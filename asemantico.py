
# ==========================================
# JARVIS - ANALIZADOR SEMANTICO
# ETAPA 1: TIPOS DE DATOS Y VARIABLES
# ==========================================

from lexer import lexer
from parser import parser, codigo


class ErrorSemantico(Exception):
    pass


# TABLA DE SIMBOLOS
tabla_simbolos = {}


# 1. IDENTIFICAR EL TIPO DE UN VALOR

def obtener_tipo(valor):

    if isinstance(valor, dict):

        tipo = valor.get("tipo")

        if tipo == "operacion":

            izquierda = obtener_tipo(valor["izquierda"])
            derecha = obtener_tipo(valor["derecha"])
            operador = valor["operador"]

            numericos = ("entero", "decimal")

            if izquierda not in numericos or derecha not in numericos:
                raise ErrorSemantico(
                    f"No se puede realizar '{operador}' "
                    f"entre {izquierda} y {derecha}"
                )

            if operador == "/":
                return "decimal"

            if izquierda == "decimal" or derecha == "decimal":
                return "decimal"

            return "entero"

        if tipo == "comparacion":

            izquierda = obtener_tipo(valor["izquierda"])
            derecha = obtener_tipo(valor["derecha"])

            numericos = ("entero", "decimal")

            compatibles = (
                izquierda == derecha
                or (
                    izquierda in numericos
                    and derecha in numericos
                )
            )

            if not compatibles:
                raise ErrorSemantico(
                    f"No se pueden comparar "
                    f"{izquierda} y {derecha}"
                )

            return "logico"

    # Numeros enteros
    if isinstance(valor, int) and not isinstance(valor, bool):
        return "entero"

    # Numeros decimales
    if isinstance(valor, float):
        return "decimal"

    # Valores logicos mexicanos
    if valor in ("si paso", "no paso"):
        return "logico"

    if isinstance(valor, str):

        # Variable previamente declarada
        if valor in tabla_simbolos:
            return tabla_simbolos[valor]["tipo"]

        # En esta etapa, los otros textos se tratan
        # como cadenas literales.
        return "cadenita"

    raise ErrorSemantico("Tipo de dato desconocido")


# 2. VERIFICAR COMPATIBILIDAD DE TIPOS

def tipos_compatibles(declarado, encontrado):

    if declarado == encontrado:
        return True

    # Un entero puede almacenarse como decimal
    if declarado == "decimal" and encontrado == "entero":
        return True

    return False


# 3. ANALIZAR CADA INSTRUCCION

def analizar_instruccion(instruccion):

    tipo = instruccion["tipo"]

    # DECLARACIONES DE VARIABLES
    if tipo == "variable":

        nombre = instruccion["nombre"]
        tipo_declarado = instruccion["dato"]
        valor = instruccion["valor"]

        if nombre in tabla_simbolos:
            raise ErrorSemantico(
                f"La variable '{nombre}' ya fue declarada"
            )

        tipo_encontrado = obtener_tipo(valor)

        if not tipos_compatibles(
            tipo_declarado, tipo_encontrado
        ):
            raise ErrorSemantico(
                f"La variable '{nombre}' es de tipo "
                f"'{tipo_declarado}', pero recibe "
                f"un valor de tipo '{tipo_encontrado}'"
            )

        tabla_simbolos[nombre] = {
            "tipo": tipo_declarado,
            "valor": valor
        }

    # IMPRIMIR
    elif tipo == "imprimir":
        obtener_tipo(instruccion["mensaje"])

    # CONDICIONES
    elif tipo == "si":

        tipo_condicion = obtener_tipo(
            instruccion["condicion"]
        )

        if tipo_condicion != "logico":
            raise ErrorSemantico(
                "La condicion SI debe ser logica"
            )

        # Analizar instrucciones del bloque SI
        for elemento in instruccion["instrucciones_si"]:
            analizar_instruccion(elemento)

        # Analizar instrucciones del bloque SINO
        for elemento in instruccion["instrucciones_sino"]:
            analizar_instruccion(elemento)


# 4. ANALIZAR EL PROGRAMA COMPLETO

def analizar_programa(arbol):

    tabla_simbolos.clear()

    instrucciones = arbol["mision"]["instrucciones"]

    for instruccion in instrucciones:
        analizar_instruccion(instruccion)

    return tabla_simbolos


# 5. EJECUTAR EL ANALISIS SEMANTICO

if __name__ == "__main__":

    try:

        lexer.lineno = 1

        arbol = parser.parse(
            codigo,
            lexer=lexer
        )

        if arbol is None:
            raise SyntaxError(
                "No se pudo analizar el programa"
            )

        resultado = analizar_programa(arbol)

        print("========== JARVIS ==========")
        print("Analisis semantico correcto")
        print("\nTabla de simbolos:")

        for nombre, datos in resultado.items():

            print(
                f"Variable: {nombre} | "
                f"Tipo: {datos['tipo']}"
            )

        print("\nSin errores semanticos detectados")

    except (SyntaxError, ErrorSemantico) as error:

        print("========== JARVIS ==========")
        print("Error detectado:")
        print(error)
