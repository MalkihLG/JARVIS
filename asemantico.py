
# ==========================================
# JARVIS - ANALIZADOR SEMANTICO
# ETAPA 2: VARIABLES, ASIGNACIONES,
# OPERACIONES, CONDICIONES Y CICLOS
# ==========================================

from lexer import lexer
from parser import parser, codigo


class ErrorSemantico(Exception):
    pass


# 1. TABLA DE SIMBOLOS

tabla_simbolos = {}


# 2. OBTENER TIPO DE DATO

def obtener_tipo(valor):

    if isinstance(valor, dict):

        tipo = valor.get("tipo")

        if tipo in ("operacion", "comparacion"):

            izquierda = obtener_tipo(valor["izquierda"])
            derecha = obtener_tipo(valor["derecha"])
            operador = valor["operador"]

            numericos = ("entero", "decimal")

            if tipo == "operacion":

                if izquierda not in numericos or derecha not in numericos:
                    raise ErrorSemantico(
                        f"Operacion '{operador}' invalida "
                        f"entre {izquierda} y {derecha}"
                    )

                if operador == "/":
                    return "decimal"

                if "decimal" in (izquierda, derecha):
                    return "decimal"

                return "entero"

            if operador in ("==", "!="):

                if izquierda == derecha:
                    return "logico"

                if izquierda in numericos and derecha in numericos:
                    return "logico"

                raise ErrorSemantico(
                    "Comparacion entre tipos incompatibles"
                )

            if izquierda not in numericos or derecha not in numericos:
                raise ErrorSemantico(
                    f"La comparacion '{operador}' "
                    "requiere valores numericos"
                )

            return "logico"

        raise ErrorSemantico(
            f"Expresion desconocida: {tipo}"
        )

    if isinstance(valor, bool):
        return "logico"

    if isinstance(valor, int):
        return "entero"

    if isinstance(valor, float):
        return "decimal"

    if isinstance(valor, str):

        if valor in ("si paso", "no paso"):
            return "logico"

        if valor in tabla_simbolos:
            return tabla_simbolos[valor]["tipo"]

        return "cadenita"

    raise ErrorSemantico("Tipo de dato desconocido")


# 3. COMPATIBILIDAD DE TIPOS

def tipos_compatibles(declarado, encontrado):

    if declarado == encontrado:
        return True

    if declarado == "decimal" and encontrado == "entero":
        return True

    return False


# 4. ANALIZAR INSTRUCCIONES

def analizar_instruccion(instruccion):

    tipo = instruccion["tipo"]

    # DECLARACION DE VARIABLES
    if tipo == "variable":

        nombre = instruccion["nombre"]
        declarado = instruccion["dato"]
        valor = instruccion["valor"]

        if nombre in tabla_simbolos:
            raise ErrorSemantico(
                f"La variable '{nombre}' ya existe"
            )

        encontrado = obtener_tipo(valor)

        if not tipos_compatibles(declarado, encontrado):
            raise ErrorSemantico(
                f"La variable '{nombre}' es {declarado}, "
                f"pero recibe {encontrado}"
            )

        tabla_simbolos[nombre] = {
            "tipo": declarado,
            "valor": valor
        }

    # ACTUALIZAR VARIABLES
    elif tipo == "asignacion":

        nombre = instruccion["nombre"]
        operador = instruccion["operador"]
        valor = instruccion["valor"]

        if nombre not in tabla_simbolos:
            raise ErrorSemantico(
                f"La variable '{nombre}' no existe"
            )

        declarado = tabla_simbolos[nombre]["tipo"]
        encontrado = obtener_tipo(valor)

        if operador == "=":

            if not tipos_compatibles(declarado, encontrado):
                raise ErrorSemantico(
                    f"No se puede asignar {encontrado} "
                    f"a una variable {declarado}"
                )

        elif operador in ("+=", "-=", "*=", "/="):

            numericos = ("entero", "decimal")

            if declarado not in numericos or encontrado not in numericos:
                raise ErrorSemantico(
                    f"El operador '{operador}' "
                    "requiere valores numericos"
                )

            if operador == "/=" and declarado == "entero":
                raise ErrorSemantico(
                    "Una division puede generar decimales. "
                    "Utiliza una variable decimal"
                )

            if declarado == "entero" and encontrado == "decimal":
                raise ErrorSemantico(
                    "No puedes guardar un resultado decimal "
                    "en una variable entera"
                )

        else:
            raise ErrorSemantico(
                f"Operador no reconocido: {operador}"
            )

    # IMPRIMIR
    elif tipo == "imprimir":
        obtener_tipo(instruccion["mensaje"])

    # CONDICION SI / SINO
    elif tipo == "si":

        condicion = obtener_tipo(
            instruccion["condicion"]
        )

        if condicion != "logico":
            raise ErrorSemantico(
                "La condicion SI debe ser logica"
            )

        for elemento in instruccion["instrucciones_si"]:
            analizar_instruccion(elemento)

        for elemento in instruccion["instrucciones_sino"]:
            analizar_instruccion(elemento)

    # CICLO REPETIR
    elif tipo == "repetir":

        cantidad = obtener_tipo(
            instruccion["cantidad"]
        )

        if cantidad != "entero":
            raise ErrorSemantico(
                "REPETIR necesita una cantidad entera"
            )

        for elemento in instruccion["instrucciones"]:
            analizar_instruccion(elemento)


    # CICLO MIENTRAS
    elif tipo == "mientras":

        tipo_condicion = obtener_tipo(
            instruccion["condicion"]
        )

        if tipo_condicion != "logico":
            raise ErrorSemantico(
                "La condicion MIENTRAS debe ser logica"
            )

        for elemento in instruccion["instrucciones"]:
            analizar_instruccion(elemento)


    else:
        raise ErrorSemantico(
            f"Instruccion no implementada: {tipo}"
        )



# 5. ANALIZAR PROGRAMA COMPLETO

def analizar_programa(arbol):

    tabla_simbolos.clear()

    instrucciones = arbol["mision"]["instrucciones"]

    for instruccion in instrucciones:
        analizar_instruccion(instruccion)

    return tabla_simbolos


# 6. EJECUTAR ANALISIS SEMANTICO

if __name__ == "__main__":

    try:
        lexer.lineno = 1

        arbol = parser.parse(
            codigo,
            lexer=lexer
        )

        if arbol is None:
            raise SyntaxError(
                "No se pudo construir el AST"
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

        print("\nAsignaciones validadas correctamente")
        print("Sin errores semanticos detectados")

    except (SyntaxError, ErrorSemantico) as error:

        print("========== ERROR JARVIS ==========")
        print(error)
