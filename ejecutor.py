
# ==========================================
# JARVIS - EJECUTOR DE PROGRAMAS
# ETAPA 1: VARIABLES, OPERACIONES Y DECISIONES
# ==========================================

from lexer import lexer
from parser import parser, codigo
from asemantico import analizar_programa, ErrorSemantico


class EjecutorJARVIS:

    def __init__(self):
        self.variables = {}

    # 1. OBTENER VALORES
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

        # VALORES LOGICOS DE JARVIS
        if expresion == "si paso":
            return True

        if expresion == "no paso":
            return False

        # CONSULTAR VARIABLES
        if isinstance(expresion, str):

            if expresion in self.variables:
                return self.variables[expresion]

            return expresion

        return expresion

    # 2. MOSTRAR VALORES
    def convertir_salida(self, valor):

        if valor is True:
            return "si paso"

        if valor is False:
            return "no paso"

        return str(valor)

    # 3. EJECUTAR INSTRUCCIONES
    def ejecutar_instruccion(self, instruccion):

        tipo = instruccion["tipo"]

        # DECLARAR VARIABLES
        if tipo == "variable":

            nombre = instruccion["nombre"]

            valor = self.evaluar(
                instruccion["valor"]
            )

            self.variables[nombre] = valor

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
                    "La condicion debe ser logica"
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

        else:
            raise ValueError(
                f"Instruccion no implementada: {tipo}"
            )

    # 4. EJECUTAR LA MISION PRINCIPAL
    def ejecutar_programa(self, arbol):

        print("========== JARVIS ==========")
        print("Sistema:", arbol["nombre"])
        print("Ejecutando mision principal...")
        print()

        instrucciones = arbol["mision"][
            "instrucciones"
        ]

        for instruccion in instrucciones:
            self.ejecutar_instruccion(instruccion)

        print()
        print("Mision finalizada correctamente")


# 5. INICIAR JARVIS
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

        # ANALISIS SEMANTICO PREVIO
        analizar_programa(arbol)

        # EJECUTAR
        jarvis = EjecutorJARVIS()
        jarvis.ejecutar_programa(arbol)

    except (
        SyntaxError,
        ErrorSemantico,
        ValueError,
        TypeError,
        ZeroDivisionError
    ) as error:

        print("========== ERROR JARVIS ==========")
        print(error)
