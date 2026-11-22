
# ==========================================
# JARVIS - EJECUTOR DE PROGRAMAS
# ETAPA 4: VARIABLES, OPERACIONES,
# ASIGNACIONES, DECISIONES, CICLOS
# Y FUNCIONES ACCION
# ==========================================

from lexer import lexer
from parser import parser, codigo
from asemantico import analizar_programa, ErrorSemantico


class EjecutorJARVIS:

    # ======================================
    # 1. INICIALIZAR EJECUTOR
    # ======================================

    def __init__(self):

        self.variables = {}
        self.acciones = {}
        self.pila_acciones = []

    # ======================================
    # 2. EVALUAR EXPRESIONES
    # ======================================

    def evaluar(self, expresion):

        if isinstance(expresion, dict):

            tipo = expresion["tipo"]


            # IDENTIFICADORES DE VARIABLES
            if tipo == "identificador":

                nombre = expresion["nombre"]

                if nombre not in self.variables:
                    raise ValueError(
                        f"La variable '{nombre}' no existe"
                    )

                return self.variables[nombre]

            if tipo in ("operacion", "comparacion"):

                izquierda = self.evaluar(
                    expresion["izquierda"]
                )

                derecha = self.evaluar(
                    expresion["derecha"]
                )

                operador = expresion["operador"]

                # OPERACIONES MATEMATICAS

                if operador == "+":
                    return izquierda + derecha

                if operador == "-":
                    return izquierda - derecha

                if operador == "*":
                    return izquierda * derecha

                if operador == "/":
                    return izquierda / derecha

                # COMPARACIONES

                if operador == "==":
                    return izquierda == derecha

                if operador == "!=":
                    return izquierda != derecha

                if operador == ">":
                    return izquierda > derecha

                if operador == "<":
                    return izquierda < derecha

                if operador == ">=":
                    return izquierda >= derecha

                if operador == "<=":
                    return izquierda <= derecha

                raise ValueError(
                    f"Operador desconocido: {operador}"
                )

            raise ValueError(
                f"Expresion no implementada: {tipo}"
            )

        # VALORES LOGICOS DE JARVIS

        if isinstance(expresion, str):

            if expresion == "si paso":
                return True

            if expresion == "no paso":
                return False

            # CONSULTAR VARIABLES
            if expresion in self.variables:
                return self.variables[expresion]

            # CADENAS LITERALES
            return expresion

        return expresion

    # ======================================
    # 3. CONVERTIR VALORES
    # ======================================

    def convertir_salida(self, valor):

        if valor is True:
            return "si paso"

        if valor is False:
            return "no paso"

        return str(valor)

    # ======================================
    # 4. REGISTRAR FUNCIONES
    # ======================================

    def registrar_acciones(self, arbol):

        self.acciones.clear()

        for accion in arbol.get("acciones", []):

            nombre = accion["nombre"]

            if nombre in self.acciones:
                raise ValueError(
                    f"La accion '{nombre}' ya existe"
                )

            self.acciones[nombre] = accion


    # ======================================
    # EJECUTAR UNA ACCION CON PARAMETROS
    # ======================================

    def ejecutar_accion(self, nombre, argumentos=None):

        if nombre not in self.acciones:
            raise ValueError(
                f"La accion '{nombre}' no existe"
            )

        accion = self.acciones[nombre]

        parametros = accion.get("parametros", [])
        argumentos = argumentos if argumentos is not None else []

        if len(parametros) != len(argumentos):
            raise ValueError(
                f"La accion '{nombre}' espera "
                f"{len(parametros)} argumento(s)"
            )

        # EVALUAR LOS ARGUMENTOS
        valores = [
            self.evaluar(argumento)
            for argumento in argumentos
        ]

        if len(self.pila_acciones) >= 100:
            raise ValueError(
                "Limite de llamadas a acciones superado"
            )

        # GUARDAR VALORES ANTERIORES
        anteriores = {}

        for parametro, valor in zip(parametros, valores):

            nombre_parametro = parametro["nombre"]

            anteriores[nombre_parametro] = (
                nombre_parametro in self.variables,
                self.variables.get(nombre_parametro)
            )

            self.variables[nombre_parametro] = valor

        self.pila_acciones.append(nombre)

        try:
            for instruccion in accion["instrucciones"]:
                self.ejecutar_instruccion(instruccion)

        finally:
            # RESTAURAR LAS VARIABLES ANTERIORES
            for variable, (existia, valor) in anteriores.items():

                if existia:
                    self.variables[variable] = valor
                else:
                    self.variables.pop(variable, None)

            self.pila_acciones.pop()


    # ======================================
    # 6. EJECUTAR INSTRUCCIONES
    # ======================================

    def ejecutar_instruccion(self, instruccion):

        tipo = instruccion["tipo"]

        # DECLARACION DE VARIABLES

        if tipo == "variable":

            nombre = instruccion["nombre"]

            valor = self.evaluar(
                instruccion["valor"]
            )

            self.variables[nombre] = valor

        # ACTUALIZACION DE VARIABLES

        elif tipo == "asignacion":

            nombre = instruccion["nombre"]
            operador = instruccion["operador"]

            valor_nuevo = self.evaluar(
                instruccion["valor"]
            )

            if nombre not in self.variables:
                raise ValueError(
                    f"La variable '{nombre}' no existe"
                )

            valor_actual = self.variables[nombre]

            if operador == "=":
                resultado = valor_nuevo

            elif operador == "+=":
                resultado = valor_actual + valor_nuevo

            elif operador == "-=":
                resultado = valor_actual - valor_nuevo

            elif operador == "*=":
                resultado = valor_actual * valor_nuevo

            elif operador == "/=":
                resultado = valor_actual / valor_nuevo

            else:
                raise ValueError(
                    f"Operador desconocido: {operador}"
                )

            self.variables[nombre] = resultado

        # IMPRIMIR RESULTADOS

        elif tipo == "imprimir":

            valor = self.evaluar(
                instruccion["mensaje"]
            )

            print(self.convertir_salida(valor))

        # CONDICIONES SI Y SINO

        elif tipo == "si":

            condicion = self.evaluar(
                instruccion["condicion"]
            )

            if not isinstance(condicion, bool):
                raise TypeError(
                    "La condicion SI debe ser logica"
                )

            if condicion:
                instrucciones = instruccion[
                    "instrucciones_si"
                ]

            else:
                instrucciones = instruccion[
                    "instrucciones_sino"
                ]

            for elemento in instrucciones:
                self.ejecutar_instruccion(elemento)

        # CICLO REPETIR

        elif tipo == "repetir":

            cantidad = self.evaluar(
                instruccion["cantidad"]
            )

            if type(cantidad) is not int or cantidad < 0:
                raise ValueError(
                    "REPETIR necesita un entero no negativo"
                )

            if cantidad > 10000:
                raise ValueError(
                    "REPETIR supero el limite permitido"
                )

            for i in range(cantidad):

                for elemento in instruccion["instrucciones"]:
                    self.ejecutar_instruccion(elemento)

        # CICLO MIENTRAS

        elif tipo == "mientras":

            iteraciones = 0

            while True:

                condicion = self.evaluar(
                    instruccion["condicion"]
                )

                if not isinstance(condicion, bool):
                    raise TypeError(
                        "La condicion MIENTRAS debe ser logica"
                    )

                if not condicion:
                    break

                iteraciones += 1

                if iteraciones > 10000:
                    raise ValueError(
                        "MIENTRAS supero el limite de 10000 repeticiones"
                    )

                for elemento in instruccion["instrucciones"]:
                    self.ejecutar_instruccion(elemento)

        # LLAMADAS A FUNCIONES ACCION

        elif tipo == "llamada":

            nombre = instruccion["nombre"]

            argumentos = instruccion.get("argumentos", [])

            self.ejecutar_accion(nombre, argumentos)

        # INSTRUCCIONES DESCONOCIDAS

        else:
            raise ValueError(
                f"Instruccion no implementada: {tipo}"
            )

    # ======================================
    # 7. EJECUTAR MISION PRINCIPAL
    # ======================================

    def ejecutar_programa(self, arbol):

        # REGISTRAR ACCIONES DISPONIBLES
        self.registrar_acciones(arbol)

        print("========== JARVIS ==========")
        print("Sistema:", arbol["nombre"])
        print("Ejecutando mision principal...")
        print()

        instrucciones = arbol["mision"]["instrucciones"]

        for instruccion in instrucciones:
            self.ejecutar_instruccion(instruccion)

        print()
        print("Mision finalizada correctamente")


# ==========================================
# 8. INICIAR JARVIS
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
        analizar_programa(arbol)

        # CREAR EJECUTOR
        jarvis = EjecutorJARVIS()

        # EJECUTAR MISION
        jarvis.ejecutar_programa(arbol)

        # COMPROBACION TEMPORAL
        print(
            "Energia final de la prueba:",
            jarvis.variables.get("energia")
        )

    except (
        SyntaxError,
        ErrorSemantico,
        ValueError,
        TypeError,
        ZeroDivisionError,
        RecursionError
    ) as error:

        print("========== ERROR JARVIS ==========")
        print(error)
