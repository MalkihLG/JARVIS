

# ==========================================
# JARVIS - ANALIZADOR SEMANTICO
# ETAPA 3: VARIABLES, OPERACIONES,
# ASIGNACIONES, CONDICIONES, CICLOS
# Y FUNCIONES ACCION
# ==========================================

from lexer import lexer
from parser import parser, codigo


# ==========================================
# 1. ERRORES SEMANTICOS
# ==========================================

class ErrorSemantico(Exception):
    pass


# ==========================================
# 2. TABLAS DE SIMBOLOS Y ACCIONES
# ==========================================

tabla_simbolos = {}
tabla_acciones = {}


# ==========================================
# 3. IDENTIFICAR TIPOS DE DATOS
# ==========================================

def obtener_tipo(valor):

    # EXPRESIONES Y COMPARACIONES
    if isinstance(valor, dict):

        tipo = valor.get("tipo")

        if tipo in ("operacion", "comparacion"):

            izquierda = obtener_tipo(
                valor["izquierda"]
            )

            derecha = obtener_tipo(
                valor["derecha"]
            )

            operador = valor["operador"]
            numericos = ("entero", "decimal")

            # OPERACIONES MATEMATICAS
            if tipo == "operacion":

                if (izquierda not in numericos
                        or derecha not in numericos):

                    raise ErrorSemantico(
                        f"Operacion '{operador}' invalida "
                        f"entre {izquierda} y {derecha}"
                    )

                if operador == "/":
                    return "decimal"

                if operador == "%":
                    if ("decimal" in (izquierda, derecha)):
                        return "decimal"
                    return "entero"

                if operador == "**":
                    if ("decimal" in (izquierda, derecha)):
                        return "decimal"
                    return "entero"

                if ("decimal" in (izquierda, derecha)):
                    return "decimal"

                return "entero"

            # COMPARACIONES DE IGUALDAD
            if operador in ("==", "!="):

                if izquierda == derecha:
                    return "logico"

                if (izquierda in numericos
                        and derecha in numericos):
                    return "logico"

                raise ErrorSemantico(
                    "Comparacion entre tipos incompatibles"
                )

            # COMPARACIONES NUMERICAS
            if (izquierda not in numericos
                    or derecha not in numericos):

                raise ErrorSemantico(
                    f"La comparacion '{operador}' "
                    "requiere valores numericos"
                )

            return "logico"

        raise ErrorSemantico(
            f"Expresion desconocida: {tipo}"
        )

    # VALORES LOGICOS DE PYTHON
    if isinstance(valor, bool):
        return "logico"

    # NUMEROS ENTEROS
    if isinstance(valor, int):
        return "entero"

    # NUMEROS DECIMALES
    if isinstance(valor, float):
        return "decimal"

    # CADENAS Y VALORES LOGICOS JARVIS
    if isinstance(valor, str):

        if valor in ("si paso", "no paso"):
            return "logico"

        # CONSULTAR VARIABLE DECLARADA
        if valor in tabla_simbolos:
            return tabla_simbolos[valor]["tipo"]

        return "cadenita"

    raise ErrorSemantico(
        "Tipo de dato desconocido"
    )


# ==========================================
# 4. COMPROBAR COMPATIBILIDAD DE TIPOS
# ==========================================

def tipos_compatibles(declarado, encontrado):

    if declarado == encontrado:
        return True

    # UN ENTERO PUEDE GUARDARSE COMO DECIMAL
    if (declarado == "decimal"
            and encontrado == "entero"):
        return True

    return False


# ==========================================
# 5. ANALIZAR INSTRUCCIONES
# ==========================================

def analizar_instruccion(instruccion):

    tipo = instruccion["tipo"]

    # --------------------------------------
    # DECLARACION DE VARIABLES
    # --------------------------------------

    if tipo == "variable":

        nombre = instruccion["nombre"]
        declarado = instruccion["dato"]
        valor = instruccion["valor"]

        if nombre in tabla_simbolos:

            raise ErrorSemantico(
                f"La variable '{nombre}' ya existe"
            )

        encontrado = obtener_tipo(valor)

        if not tipos_compatibles(
            declarado,
            encontrado
        ):

            raise ErrorSemantico(
                f"La variable '{nombre}' es "
                f"de tipo {declarado}, "
                f"pero recibe {encontrado}"
            )

        tabla_simbolos[nombre] = {
            "tipo": declarado,
            "valor": valor
        }

    # --------------------------------------
    # ACTUALIZACION DE VARIABLES
    # --------------------------------------

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

        # ASIGNACION NORMAL
        if operador == "=":

            if not tipos_compatibles(
                declarado,
                encontrado
            ):

                raise ErrorSemantico(
                    f"No se puede asignar {encontrado} "
                    f"a una variable {declarado}"
                )

        # ASIGNACIONES MATEMATICAS
        elif operador in (
            "+=",
            "-=",
            "*=",
            "/="
        ):

            numericos = ("entero", "decimal")

            if (declarado not in numericos
                    or encontrado not in numericos):

                raise ErrorSemantico(
                    f"El operador '{operador}' "
                    "requiere valores numericos"
                )

            if (operador == "/="
                    and declarado == "entero"):

                raise ErrorSemantico(
                    "Una division puede generar "
                    "decimales. Utiliza una "
                    "variable decimal"
                )

            if (declarado == "entero"
                    and encontrado == "decimal"):

                raise ErrorSemantico(
                    "No se puede guardar un decimal "
                    "en una variable entera"
                )

        else:

            raise ErrorSemantico(
                f"Operador no reconocido: {operador}"
            )

    # --------------------------------------
    # INSTRUCCION IMPRIMIR
    # --------------------------------------

    elif tipo == "imprimir":

        obtener_tipo(
            instruccion["mensaje"]
        )

    # --------------------------------------
    # CONDICION SI / SINO
    # --------------------------------------

    elif tipo == "si":

        tipo_condicion = obtener_tipo(
            instruccion["condicion"]
        )

        if tipo_condicion != "logico":

            raise ErrorSemantico(
                "La condicion SI debe ser logica"
            )

        for elemento in instruccion["instrucciones_si"]:
            analizar_instruccion(elemento)

        for elemento in instruccion["instrucciones_sino"]:
            analizar_instruccion(elemento)

    # --------------------------------------
    # CICLO REPETIR
    # --------------------------------------

    elif tipo == "repetir":

        tipo_cantidad = obtener_tipo(
            instruccion["cantidad"]
        )

        if tipo_cantidad != "entero":

            raise ErrorSemantico(
                "REPETIR necesita una cantidad entera"
            )

        for elemento in instruccion["instrucciones"]:
            analizar_instruccion(elemento)

    # --------------------------------------
    # CICLO MIENTRAS
    # --------------------------------------

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

    # --------------------------------------
    # LLAMADAS A FUNCIONES
    # --------------------------------------

    elif tipo == "llamada":

        nombre = instruccion["nombre"]

        # COMPROBAR QUE LA ACCION EXISTA
        if nombre not in tabla_acciones:
            raise ErrorSemantico(
                f"La accion '{nombre}' no existe"
            )

        # OBTENER LOS PARAMETROS DECLARADOS
        accion = tabla_acciones[nombre]

        parametros = accion.get("parametros", [])

        # OBTENER LOS ARGUMENTOS ENVIADOS
        argumentos = instruccion.get("argumentos", [])

        # VALIDAR CANTIDAD DE ARGUMENTOS
        if len(argumentos) != len(parametros):
            raise ErrorSemantico(
                f"La accion '{nombre}' espera "
                f"{len(parametros)} argumento(s), "
                f"pero recibio {len(argumentos)}"
            )

        # VALIDAR TIPOS DE LOS ARGUMENTOS
        for parametro, argumento in zip(parametros, argumentos):

            tipo_esperado = parametro["tipo"]
            nombre_parametro = parametro["nombre"]
            tipo_encontrado = obtener_tipo(argumento)

            if not tipos_compatibles(
                tipo_esperado,
                tipo_encontrado
            ):
                raise ErrorSemantico(
                    f"La accion '{nombre}' espera "
                    f"{tipo_esperado} en el parametro "
                    f"'{nombre_parametro}', pero recibio "
                    f"{tipo_encontrado}"
                )


    # --------------------------------------
    # INSTRUCCIONES NO IMPLEMENTADAS
    # --------------------------------------

    else:

        raise ErrorSemantico(
            f"Instruccion no implementada: {tipo}"
        )


# ==========================================
# 6. REGISTRAR FUNCIONES DE JARVIS
# ==========================================

def registrar_acciones(arbol):

    tabla_acciones.clear()

    for accion in arbol.get("acciones", []):

        nombre = accion["nombre"]

        # EVITAR FUNCIONES DUPLICADAS
        if nombre in tabla_acciones:

            raise ErrorSemantico(
                f"La accion '{nombre}' "
                "ya fue declarada"
            )

        tabla_acciones[nombre] = accion


# ==========================================
# 7. ANALIZAR PROGRAMA COMPLETO
# ==========================================

def analizar_programa(arbol):

    # LIMPIAR TABLAS
    tabla_simbolos.clear()
    tabla_acciones.clear()

    # PRIMERO REGISTRAR LAS FUNCIONES
    registrar_acciones(arbol)

    # ANALIZAR MISION PRINCIPAL
    instrucciones = arbol["mision"]["instrucciones"]

    for instruccion in instrucciones:
        analizar_instruccion(instruccion)

    # VALIDAR TAMBIEN LOS CUERPOS
    # DE LAS FUNCIONES DECLARADAS
    simbolos_mision = tabla_simbolos.copy()

    for accion in tabla_acciones.values():

        # CONTEXTO TEMPORAL PARA LA ACCION
        tabla_simbolos.clear()
        tabla_simbolos.update(simbolos_mision)

        for parametro in accion.get("parametros", []):
            tabla_simbolos[parametro["nombre"]] = {
                "tipo": parametro["tipo"],
                "valor": None
            }

        for instruccion in accion["instrucciones"]:
            analizar_instruccion(instruccion)

    # RESTAURAR SIMBOLOS DE LA MISION
    tabla_simbolos.clear()
    tabla_simbolos.update(simbolos_mision)

    return tabla_simbolos


# ==========================================
# 8. MOSTRAR RESULTADOS
# ==========================================

def mostrar_resultados(resultado):

    print("========== JARVIS ==========")
    print("Analisis semantico correcto")

    # TABLA DE ACCIONES
    print("\nTabla de acciones:")

    if tabla_acciones:

        for nombre in tabla_acciones:
            print(
                f"Accion registrada: {nombre}()"
            )

    else:
        print("No hay acciones registradas")

    # TABLA DE SIMBOLOS
    print("\nTabla de simbolos:")

    for nombre, datos in resultado.items():

        print(
            f"Variable: {nombre} | "
            f"Tipo: {datos['tipo']}"
        )

    print("\nAsignaciones validadas correctamente")
    print("Llamadas a funciones validadas")
    print("Sin errores semanticos detectados")


# ==========================================
# 9. INICIAR ANALISIS SEMANTICO
# ==========================================

if __name__ == "__main__":

    try:

        lexer.lineno = 1

        # ANALISIS SINTACTICO
        arbol = parser.parse(
            codigo,
            lexer=lexer
        )

        if arbol is None:
            raise SyntaxError(
                "No se pudo construir el AST"
            )

        # ANALISIS SEMANTICO
        resultado = analizar_programa(arbol)

        # MOSTRAR RESULTADOS
        mostrar_resultados(resultado)

    except (
        SyntaxError,
        ErrorSemantico
    ) as error:

        print("========== ERROR JARVIS ==========")
        print(error)
