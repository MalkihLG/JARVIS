"""Analizador lexico del lenguaje JARVIS mediante PLY.

Se reconocen palabras reservadas, identificadores, valores, operadores,
delimitadores y comentarios.

La estructura y el significado de las instrucciones se comprueban
posteriormente en asintactico.py y asemantico.py.
"""

import math
import ply.lex as lex


# Aqui registro las palabras reservadas y el token que representa cada una.
reservadas = {
    # Estructura del programa y acciones.
    "sistema": "SISTEMA",
    "mision": "MISION",
    "principal": "PRINCIPAL",
    "accion": "ACCION",
    "ejecutar": "EJECUTAR",
    "devolver": "DEVOLVER",

    # Variables, tipos de datos y estructuras.
    "var": "VAR",
    "fijo": "FIJO",
    "estado": "ESTADO",
    "entero": "ENTERO",
    "decimal": "DECIMAL",
    "cadenita": "CADENITA",
    "logico": "LOGICO",
    "caracter": "CARACTER_TIPO",
    "lista": "LISTA",
    "mapa": "MAPA",
    "vacio": "VACIO",
    "nada": "NADA",

    # Entrada, salida y seguimiento del programa.
    "imprimir": "IMPRIMIR",
    "preguntar": "PREGUNTAR",
    "alerta": "ALERTA",
    "registrar": "REGISTRAR",
    "checar": "CHECAR",

    # Condiciones.
    "si": "SI",
    "sinosi": "SINOSI",
    "sino": "SINO",
    "segun": "SEGUN",
    "caso": "CASO",
    "otro_caso": "OTRO_CASO",

    # Ciclos y control de flujo.
    "para": "PARA",
    "mientras": "MIENTRAS",
    "repetir": "REPETIR",
    "detener": "DETENER",
    "seguir": "SEGUIR",
    "en": "EN",

    # Operadores escritos como palabras.
    "y": "Y",
    "o": "O",
    "negar": "NEGAR",
    "div": "DIV_ENTERA",

    # Manejo de errores.
    "vigilar": "VIGILAR",
    "proteger": "PROTEGER",
    "atrapar": "ATRAPAR",
    "lanzar": "LANZAR",
    "finalmente": "FINALMENTE",

    # Clases y objetos.
    "clase": "CLASE",
    "crear": "CREAR",
    "este": "ESTE",
    "iniciar": "INICIAR",
    "publico": "PUBLICO",
    "privado": "PRIVADO",
    "hereda": "HEREDA",

    # Modulos y estructuras personalizadas.
    "usar": "USAR",
    "modulo": "MODULO",
    "estructura": "ESTRUCTURA",
    "enumeracion": "ENUMERACION",
}


# Mantengo los nombres originales: otros modulos ya los utilizan.
tokens = [
    "IDENTIFICADOR", "NUMERO", "CADENA", "CARACTER",
    "SI_PASO", "NO_PASO",

    "SUMA", "RESTA", "MULTIPLICACION", "DIVISION",
    "RESIDUO", "POTENCIA",

    "IGUAL", "DIFERENTE", "MAYOR", "MENOR",
    "MAYORIGUAL", "MENORIGUAL",

    "ASIGNAR", "MASIGUAL", "MENOSIGUAL", "PORIGUAL", "DIVIGUAL",

    "PARIZQ", "PARDER", "LLAVEIZQ", "LLAVEDER",
    "CORCHETEIZQ", "CORCHETEDER",
    "PUNTOYCOMA", "DOSPUNTOS", "COMA", "PUNTO", "FLECHA",
] + list(reservadas.values())


# Los operadores compuestos deben reconocerse antes que sus versiones simples.
t_POTENCIA = r"\*\*"
t_MASIGUAL = r"\+="
t_MENOSIGUAL = r"-="
t_PORIGUAL = r"\*="
t_DIVIGUAL = r"/="

t_IGUAL = r"=="
t_DIFERENTE = r"!="
t_MAYORIGUAL = r">="
t_MENORIGUAL = r"<="
t_FLECHA = r"->"

t_SUMA = r"\+"
t_RESTA = r"-"
t_MULTIPLICACION = r"\*"
t_DIVISION = r"/"
t_RESIDUO = r"%"
t_MAYOR = r">"
t_MENOR = r"<"
t_ASIGNAR = r"="

# Delimitadores.
t_PARIZQ = r"\("
t_PARDER = r"\)"
t_LLAVEIZQ = r"\{"
t_LLAVEDER = r"\}"
t_CORCHETEIZQ = r"\["
t_CORCHETEDER = r"\]"
t_PUNTOYCOMA = r";"
t_DOSPUNTOS = r":"
t_COMA = r","
t_PUNTO = r"\."

# Los espacios, tabulaciones y retornos de carro no producen tokens.
t_ignore = " \t\r"


def _informar_error(t, descripcion):
    """Mantengo el formato de mensajes utilizado por la interfaz actual."""
    print(f"Error lexico en la linea {t.lineno}: {descripcion}")


# Primero detecto los literales logicos escritos con dos palabras.
def t_SI_PASO(t):
    r"si[ \t]+paso\b"
    return t


def t_NO_PASO(t):
    r"no[ \t]+paso\b"
    return t


# Ignoro los comentarios que terminan al llegar a un salto de linea.
def t_COMENTARIO_LINEA(t):
    r"//[^\n]*"
    pass


# Busco el cierre de los comentarios de bloque y cuento sus saltos de linea.
# Tambien detecto cuando el comentario llega al final sin cerrar.
def t_COMENTARIO_BLOQUE(t):
    r"/\*"
    datos = t.lexer.lexdata
    inicio_contenido = t.lexer.lexpos
    cierre = datos.find("*/", inicio_contenido)

    if cierre == -1:
        _informar_error(t, "comentario de bloque sin cerrar")
        t.lexer.lineno += datos[inicio_contenido:].count("\n")
        t.lexer.lexpos = len(datos)
        return

    t.lexer.lineno += datos[inicio_contenido:cierre + 2].count("\n")
    t.lexer.lexpos = cierre + 2


# Devuelvo la cadena con comillas para conservar el formato anterior.
def t_CADENA(t):
    r'"([^"\\\n]|\\.)*"'
    return t


# Si una cadena no cierra antes del fin de la linea, reporto el problema.
def t_CADENA_SIN_CERRAR(t):
    r'"[^\n]*'
    _informar_error(t, "cadena de texto sin cerrar")


# El caracter puede ser uno normal o un caracter escapado.
def t_CARACTER(t):
    r"'([^'\\\n]|\\.)'"
    return t


# Los caracteres con mas de un simbolo o sin cierre no son validos.
def t_CARACTER_INVALIDO(t):
    r"'[^\n]*"
    _informar_error(t, "literal de caracter invalido o sin cerrar")


# Reconozco enteros, decimales y notacion cientifica.
# Todos se conservan como int o float para los modulos existentes.
def t_NUMERO(t):
    r"(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?"
    try:
        if "." in t.value or "e" in t.value.lower():
            t.value = float(t.value)
            if not math.isfinite(t.value):
                raise ValueError("numero fuera de rango")
        else:
            t.value = int(t.value)
    except (ValueError, OverflowError):
        _informar_error(t, "numero invalido o fuera de rango")
        return None
    return t


# Las palabras reservadas tienen prioridad sobre un identificador normal.
def t_IDENTIFICADOR(t):
    r"[a-zA-Z_][a-zA-Z0-9_]*"
    t.type = reservadas.get(t.value, "IDENTIFICADOR")
    return t


# Cada salto de linea incrementa su posicion en el codigo.
def t_newline(t):
    r"\n+"
    t.lexer.lineno += len(t.value)


# Un simbolo que no pertenece al lenguaje genera un mensaje de error.
def t_error(t):
    _informar_error(t, f"caracter no reconocido '{t.value[0]}'")
    t.lexer.skip(1)


# Este objeto sigue siendo el que importan los demas archivos de JARVIS.
lexer = lex.lex()


# Solo es un ejemplo para probar los tokens, no para ejecutar el programa.
codigo = '''
sistema StarkLab {

    fijo energiaMaxima: entero = 100;
    estado energia: entero = 100;

    var trajeListo: logico = si paso;
    var enemigo: logico = no paso;
    var heroe: cadenita = "Iron Man";

    // Se revisa el estado del sistema.

    /* Comentario
       de varias lineas. */

    accion usarPropulsor(consumo: entero) {

        energia -= consumo;

        registrar("Propulsor activado");
    }

    mision principal {

        imprimir("Bienvenido a JARVIS");

        si (trajeListo == si paso) {

            imprimir(heroe);

        } sinosi (energia < 30) {

            alerta("Energia baja");

        } sino {

            imprimir("Sistema preparado");
        }
    }
}
'''


if __name__ == "__main__":
    # Compruebo el analizador sin afectar los demas modulos.
    lexer.lineno = 1
    lexer.input(codigo)
    print("========== TOKENS DE JARVIS ==========")
    for token in lexer:
        print(f"{token.type:20} | {token.value}")
    print("========== FIN DEL ANALISIS ==========")