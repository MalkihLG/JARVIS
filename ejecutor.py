
# ==========================================
# JARVIS - EJECUTOR DE PROGRAMAS
# ETAPA 3: VARIABLES, ASIGNACIONES,
# OPERACIONES, DECISIONES Y CICLOS
# ==========================================

from lexer import lexer
from parser import parser, codigo
from asemantico import analizar_programa, ErrorSemantico


class EjecutorJARVIS:

    # 1. INICIALIZAR EJECUTOR

    def __init__(self):
        self.variables = {}

    # 2. EVALUAR EXPRESIONES

    def evaluar(self, expresion):

        if isinstance(expresion, dict):

            tipo = expresion["tipo"]

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

        # VALORES LOGICOS MEXICANOS

        if isinstance(expresion, str):

            if expresion == "si paso":
                return True

            if expresion == "no paso":
                return False

            # CONSULTAR VARIABLES

            if expresion in self.variables:
                return self.variables[expresion]

            return expresion

        return expresion

    # 3. CONVERTIR RESULTADOS PARA MOSTRARLOS

    def convertir_salida(self, valor):

        if valor is True:
            return "si paso"

        if valor is False:
            return "no paso"

        return str(valor)

    # 4. EJECUTAR INSTRUCCIONES

    def ejecutar_instruccion(self, instruccion):

        tipo = instruccion["tipo"]

        # DECLARAR VARIABLES

        if tipo == "variable":

            nombre = instruccion["nombre"]

            valor = self.evaluar(
                instruccion["valor"]
            )

            self.variables[nombre] = valor

        # ACTUALIZAR VARIABLES

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

            # GUARDAR NUEVO VALOR
            self.variables[nombre] = resultado

        # IMPRIMIR

        elif tipo == "imprimir":

            valor = self.evaluar(
                instruccion["mensaje"]
            )

            print(self.convertir_salida(valor))

        # CONDICIONES SI / SINO

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

            for i in range(cantidad):

                for elemento in instruccion["instrucciones"]:
                    self.ejecutar_instruccion(elemento)

        # OTRAS INSTRUCCIONES

        else:
            raise ValueError(
                f"Instruccion no implementada: {tipo}"
            )

    # 5. EJECUTAR MISION PRINCIPAL

    def ejecutar_programa(self, arbol):

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
# 6. INICIAR JARVIS
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
                "No se pudo analizar el programa"
            )

        # ANALISIS SEMANTICO
        analizar_programa(arbol)

        # EJECUTAR PROGRAMA
        jarvis = EjecutorJARVIS()

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
        ZeroDivisionError
    ) as error:

        print("========== ERROR JARVIS ==========")
        print(error)
