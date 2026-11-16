
import ply.lex as lex

# ==========================================
# JARVIS - ANALIZADOR LEXICO
# ==========================================

# 1. PALABRAS RESERVADAS

reservadas = {
    # Estructura principal
    "sistema": "SISTEMA",
    "mision": "MISION",
    "principal": "PRINCIPAL",
    "accion": "ACCION",
    "ejecutar": "EJECUTAR",
    "devolver": "DEVOLVER",

    # Variables y tipos
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

    # Entrada y salida
    "imprimir": "IMPRIMIR",
    "preguntar": "PREGUNTAR",
    "alerta": "ALERTA",
    "registrar": "REGISTRAR",
    "checar": "CHECAR",

    # Condiciones
    "si": "SI",
    "sinosi": "SINOSI",
    "sino": "SINO",
    "segun": "SEGUN",
    "caso": "CASO",
    "otro_caso": "OTRO_CASO",

    # Ciclos
    "para": "PARA",
    "mientras": "MIENTRAS",
    "repetir": "REPETIR",
    "detener": "DETENER",
    "seguir": "SEGUIR",
    "en": "EN",

    # Operadores logicos
    "y": "Y",
    "o": "O",
    "negar": "NEGAR",
    "div": "DIV_ENTERA",

    # Funciones especiales
    "vigilar": "VIGILAR",
    "proteger": "PROTEGER",
    "atrapar": "ATRAPAR",
    "lanzar": "LANZAR",
    "finalmente": "FINALMENTE",

    # Programacion orientada a objetos
    "clase": "CLASE",
    "crear": "CREAR",
    "este": "ESTE",
    "iniciar": "INICIAR",
    "publico": "PUBLICO",
    "privado": "PRIVADO",
    "hereda": "HEREDA",

    # Modulos y estructuras
    "usar": "USAR",
    "modulo": "MODULO",
    "estructura": "ESTRUCTURA",
    "enumeracion": "ENUMERACION",
}

# 2. LISTA DE TOKENS

tokens = [
    "IDENTIFICADOR",
    "NUMERO",
    "CADENA",
    "CARACTER",
    "SI_PASO",
    "NO_PASO",

    # Operadores matematicos
    "SUMA",
    "RESTA",
    "MULTIPLICACION",
    "DIVISION",
    "RESIDUO",
    "POTENCIA",

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

    # Simbolos
    "PARIZQ",
    "PARDER",
    "LLAVEIZQ",
    "LLAVEDER",
    "CORCHETEIZQ",
    "CORCHETEDER",
    "PUNTOYCOMA",
    "DOSPUNTOS",
    "COMA",
    "PUNTO",
    "FLECHA",

] + list(reservadas.values())


# 3. OPERADORES Y SIMBOLOS

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

# Ignorar espacios y tabulaciones
t_ignore = " \t"


# 4. VALORES LOGICOS MEXICANOS

def t_SI_PASO(t):
    r"si[ \t]+paso\b"
    return t


def t_NO_PASO(t):
    r"no[ \t]+paso\b"
    return t


# 5. COMENTARIOS

def t_COMENTARIO_LINEA(t):
    r"//[^\n]*"
    pass


def t_COMENTARIO_BLOQUE(t):
    r"/\*[\s\S]*?\*/"
    t.lexer.lineno += t.value.count("\n")


# 6. CADENAS Y CARACTERES

def t_CADENA(t):
    r'"([^"\\\n]|\\.)*"'
    return t


def t_CARACTER(t):
    r"'([^'\\\n]|\\.)'"
    return t


# 7. NUMEROS

def t_NUMERO(t):
    r"\d+(\.\d+)?"

    if "." in t.value:
        t.value = float(t.value)
    else:
        t.value = int(t.value)

    return t


# 8. IDENTIFICADORES

def t_IDENTIFICADOR(t):
    r"[a-zA-Z_][a-zA-Z0-9_]*"

    t.type = reservadas.get(
        t.value, "IDENTIFICADOR"
    )

    return t


# 9. SALTOS DE LINEA

def t_newline(t):
    r"\n+"
    t.lexer.lineno += len(t.value)


# 10. ERRORES LEXICOS

def t_error(t):
    print(
        f"Error lexico en la linea {t.lineno}: "
        f"caracter no reconocido '{t.value[0]}'"
    )
    t.lexer.skip(1)


# 11. CREAR EL ANALIZADOR

lexer = lex.lex()


# 12. PROGRAMA DE PRUEBA

codigo = '''
sistema StarkLab {

    fijo energiaMaxima: entero = 100;
    estado energia: entero = 100;

    var trajeListo: logico = si paso;
    var enemigo: logico = no paso;
    var heroe: cadenita = "Iron Man";

    vigilar (energia < 30) {
        alerta("Energia baja");
    }

    accion usarPropulsor(consumo: entero) {
        energia -= consumo;
        registrar("Propulsor activado");
    }

    mision principal {

        imprimir("Bienvenido a JARVIS");

        si (trajeListo == si paso) {
            imprimir(heroe);
        } sino {
            alerta("Armadura no disponible");
        }

        repetir (3) {
            usarPropulsor(25);
        }

        imprimir(energia);
    }
}
'''


# 13. MOSTRAR LOS TOKENS

if __name__ == "__main__":

    lexer.input(codigo)

    print("========== TOKENS DE JARVIS ==========")

    for token in lexer:
        print(f"{token.type:20} | {token.value}")

    print("========== FIN DEL ANALISIS ==========")
