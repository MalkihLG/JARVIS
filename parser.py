
import ply.yacc as yacc
from lexer import lexer

# ==========================================
# JARVIS - ANALIZADOR SINTACTICO
# ETAPA 6: VARIABLES, OPERACIONES,
# DECISIONES, CICLOS Y ASIGNACIONES
# ==========================================


# 1. TOKENS UTILIZADOS EN LA GRAMATICA

tokens = (
    # Estructura del programa
    "SISTEMA",
    "MISION",
    "PRINCIPAL",
    "IDENTIFICADOR",

    # Variables y tipos
    "VAR",
    "ENTERO",
    "DECIMAL",
    "CADENITA",
    "LOGICO",
    "NUMERO",
    "CADENA",
    "SI_PASO",
    "NO_PASO",

    # Entrada y salida
    "IMPRIMIR",

    # Operadores matematicos
    "SUMA",
    "RESTA",
    "MULTIPLICACION",
    "DIVISION",

    # Comparaciones
    "IGUAL",
    "DIFERENTE",
    "MAYOR",
    "MENOR",
    "MAYORIGUAL",
    "MENORIGUAL",

    # Asignaciones
    "ASIGNAR",
    "MASIGUAL",
    "MENOSIGUAL",
    "PORIGUAL",
    "DIVIGUAL",

    # Decisiones
    "SI",
    "SINO",

    # Ciclos
    "REPETIR",

    # Simbolos
    "PARIZQ",
    "PARDER",
    "LLAVEIZQ",
    "LLAVEDER",
    "PUNTOYCOMA",
    "DOSPUNTOS",
)


# 2. PRIORIDAD DE OPERADORES

precedence = (
    (
        "nonassoc",
        "IGUAL",
        "DIFERENTE",
        "MAYOR",
        "MENOR",
        "MAYORIGUAL",
        "MENORIGUAL"
    ),
    ("left", "SUMA", "RESTA"),
    ("left", "MULTIPLICACION", "DIVISION"),
)


# ==========================================
# 3. ESTRUCTURA DEL SISTEMA
# ==========================================

def p_programa(p):
    """
    programa : SISTEMA IDENTIFICADOR LLAVEIZQ mision LLAVEDER
    """

    p[0] = {
        "tipo": "sistema",
        "nombre": p[2],
        "mision": p[4]
    }


# ==========================================
# 4. MISION PRINCIPAL
# ==========================================

def p_mision(p):
    """
    mision : MISION PRINCIPAL LLAVEIZQ instrucciones LLAVEDER
    """

    p[0] = {
        "tipo": "mision",
        "nombre": "principal",
        "instrucciones": p[4]
    }


# ==========================================
# 5. LISTA DE INSTRUCCIONES
# ==========================================

def p_instrucciones_varias(p):
    """
    instrucciones : instrucciones instruccion
    """

    p[0] = p[1] + [p[2]]


def p_instrucciones_una(p):
    """
    instrucciones : instruccion
    """

    p[0] = [p[1]]


# ==========================================
# 6. DECLARACION DE VARIABLES
# ==========================================

def p_instruccion_variable(p):
    """
    instruccion : VAR IDENTIFICADOR DOSPUNTOS tipo ASIGNAR valor PUNTOYCOMA
    """

    p[0] = {
        "tipo": "variable",
        "nombre": p[2],
        "dato": p[4],
        "valor": p[6]
    }


# ==========================================
# 7. ACTUALIZACION DE VARIABLES
# ==========================================

def p_instruccion_actualizar(p):
    """
    instruccion : IDENTIFICADOR ASIGNAR valor PUNTOYCOMA
                | IDENTIFICADOR MASIGUAL valor PUNTOYCOMA
                | IDENTIFICADOR MENOSIGUAL valor PUNTOYCOMA
                | IDENTIFICADOR PORIGUAL valor PUNTOYCOMA
                | IDENTIFICADOR DIVIGUAL valor PUNTOYCOMA
    """

    p[0] = {
        "tipo": "asignacion",
        "nombre": p[1],
        "operador": p[2],
        "valor": p[3]
    }


# ==========================================
# 8. TIPOS DE DATOS
# ==========================================

def p_tipo(p):
    """
    tipo : ENTERO
         | DECIMAL
         | CADENITA
         | LOGICO
    """

    p[0] = p[1]


# ==========================================
# 9. VALORES
# ==========================================

def p_valor(p):
    """
    valor : CADENA
          | NUMERO
          | SI_PASO
          | NO_PASO
          | IDENTIFICADOR
    """

    if p.slice[1].type == "CADENA":
        p[0] = p[1][1:-1]
    else:
        p[0] = p[1]


# ==========================================
# 10. OPERACIONES MATEMATICAS
# ==========================================

def p_valor_operacion(p):
    """
    valor : valor SUMA valor
          | valor RESTA valor
          | valor MULTIPLICACION valor
          | valor DIVISION valor
    """

    p[0] = {
        "tipo": "operacion",
        "operador": p[2],
        "izquierda": p[1],
        "derecha": p[3]
    }


# ==========================================
# 11. COMPARACIONES
# ==========================================

def p_valor_comparacion(p):
    """
    valor : valor IGUAL valor
          | valor DIFERENTE valor
          | valor MAYOR valor
          | valor MENOR valor
          | valor MAYORIGUAL valor
          | valor MENORIGUAL valor
    """

    p[0] = {
        "tipo": "comparacion",
        "operador": p[2],
        "izquierda": p[1],
        "derecha": p[3]
    }


# ==========================================
# 12. EXPRESIONES CON PARENTESIS
# ==========================================

def p_valor_parentesis(p):
    """
    valor : PARIZQ valor PARDER
    """

    p[0] = p[2]


# ==========================================
# 13. INSTRUCCION IMPRIMIR
# ==========================================

def p_instruccion_imprimir(p):
    """
    instruccion : IMPRIMIR PARIZQ valor PARDER PUNTOYCOMA
    """

    p[0] = {
        "tipo": "imprimir",
        "mensaje": p[3]
    }


# ==========================================
# 14. CONDICIONES SI Y SINO
# ==========================================

def p_instruccion_si(p):
    """
    instruccion : SI PARIZQ valor PARDER LLAVEIZQ instrucciones LLAVEDER opcion_sino
    """

    p[0] = {
        "tipo": "si",
        "condicion": p[3],
        "instrucciones_si": p[6],
        "instrucciones_sino": p[8]
    }


def p_opcion_sino(p):
    """
    opcion_sino : SINO LLAVEIZQ instrucciones LLAVEDER
    """

    p[0] = p[3]


def p_opcion_sino_vacio(p):
    """
    opcion_sino :
    """

    p[0] = []


# ==========================================
# 15. CICLO REPETIR
# ==========================================

def p_instruccion_repetir(p):
    """
    instruccion : REPETIR PARIZQ valor PARDER LLAVEIZQ instrucciones LLAVEDER
    """

    p[0] = {
        "tipo": "repetir",
        "cantidad": p[3],
        "instrucciones": p[6]
    }


# ==========================================
# 16. ERRORES SINTACTICOS
# ==========================================

def p_error(p):

    if p:
        raise SyntaxError(
            f"Error sintactico en linea {p.lineno}: "
            f"token inesperado '{p.value}'"
        )

    raise SyntaxError(
        "Error sintactico: fin inesperado del programa"
    )


# ==========================================
# 17. CREAR ANALIZADOR SINTACTICO
# ==========================================

parser = yacc.yacc(
    start="programa",
    debug=False,
    write_tables=False
)


# ==========================================
# 18. MOSTRAR EXPRESIONES
# ==========================================

def mostrar_valor(valor):

    if isinstance(valor, dict):

        if valor.get("tipo") in (
            "operacion",
            "comparacion"
        ):

            izquierda = mostrar_valor(
                valor["izquierda"]
            )

            derecha = mostrar_valor(
                valor["derecha"]
            )

            return (
                f"({izquierda} "
                f"{valor['operador']} "
                f"{derecha})"
            )

    return str(valor)


# ==========================================
# 19. MOSTRAR INSTRUCCIONES
# ==========================================

def mostrar_instruccion(instruccion, nivel=0):

    espacio = "    " * nivel
    tipo = instruccion["tipo"]

    # VARIABLES
    if tipo == "variable":

        print(
            f"{espacio}Variable: {instruccion['nombre']} | "
            f"Tipo: {instruccion['dato']} | "
            f"Valor: {mostrar_valor(instruccion['valor'])}"
        )

    # ACTUALIZACION DE VARIABLES
    elif tipo == "asignacion":

        print(
            f"{espacio}Actualizar: "
            f"{instruccion['nombre']} "
            f"{instruccion['operador']} "
            f"{mostrar_valor(instruccion['valor'])}"
        )

    # IMPRIMIR
    elif tipo == "imprimir":

        print(
            f"{espacio}Imprimir: "
            f"{mostrar_valor(instruccion['mensaje'])}"
        )

    # CONDICIONES
    elif tipo == "si":

        print(
            f"{espacio}Condicion SI: "
            f"{mostrar_valor(instruccion['condicion'])}"
        )

        print(f"{espacio}Bloque SI:")

        for item in instruccion["instrucciones_si"]:
            mostrar_instruccion(item, nivel + 1)

        if instruccion["instrucciones_sino"]:

            print(f"{espacio}Bloque SINO:")

            for item in instruccion["instrucciones_sino"]:
                mostrar_instruccion(item, nivel + 1)

    # CICLO REPETIR
    elif tipo == "repetir":

        print(
            f"{espacio}Ciclo REPETIR: "
            f"{mostrar_valor(instruccion['cantidad'])} veces"
        )

        for item in instruccion["instrucciones"]:
            mostrar_instruccion(item, nivel + 1)


# ==========================================
# 20. CODIGO DE PRUEBA DE JARVIS
# ==========================================

codigo = '''
sistema StarkLab {

    mision principal {

        var heroe: cadenita = "Iron Man";
        var energia: entero = 100;

        energia -= 25;
        energia += 10;

        var armaduraLista: logico = si paso;
        var enemigos: logico = no paso;

        var resultado: entero = 10 + 5 * 2;
        var promedio: decimal = (8 + 9 + 10) / 3;

        imprimir("Bienvenido a JARVIS");
        imprimir(resultado);

        si (energia >= 50) {
            imprimir("Armadura lista");
        } sino {
            imprimir("Hay que recargar");
        }

        si (armaduraLista == si paso) {
            imprimir("Sistema preparado");
        }

        repetir (3) {
            imprimir("Escaneando la ciudad...");
        }

        imprimir("Escaneo terminado");
    }
}
'''


# ==========================================
# 21. EJECUTAR ANALISIS SINTACTICO
# ==========================================

if __name__ == "__main__":

    lexer.lineno = 1

    try:

        resultado = parser.parse(
            codigo,
            lexer=lexer
        )

        if resultado is None:
            raise SyntaxError(
                "No se pudo construir el AST"
            )

        print("========== JARVIS ==========")
        print("Analisis sintactico correcto")

        print("Sistema:", resultado["nombre"])
        print("Mision:", resultado["mision"]["nombre"])

        print("\nInstrucciones encontradas:")

        for instruccion in resultado["mision"]["instrucciones"]:
            mostrar_instruccion(instruccion)

    except SyntaxError as error:

        print("========== ERROR JARVIS ==========")
        print(error)
