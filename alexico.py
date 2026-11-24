
import ply.lex as lex


# Aqui guardo las palabras que tienen un significado especial en JARVIS.
# Cada palabra se relaciona con el token que va a reconocer el lexer.
reservadas = {

    # Estas palabras las uso para organizar el programa y sus acciones.
    "sistema": "SISTEMA",
    "mision": "MISION",
    "principal": "PRINCIPAL",
    "accion": "ACCION",
    "ejecutar": "EJECUTAR",
    "devolver": "DEVOLVER",

    # Aqui estan las palabras para declarar variables y sus tipos.
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

    # Palabras relacionadas con mostrar, pedir o registrar informacion.
    "imprimir": "IMPRIMIR",
    "preguntar": "PREGUNTAR",
    "alerta": "ALERTA",
    "registrar": "REGISTRAR",
    "checar": "CHECAR",

    # Estas palabras sirven para tomar decisiones.
    "si": "SI",
    "sinosi": "SINOSI",
    "sino": "SINO",
    "segun": "SEGUN",
    "caso": "CASO",
    "otro_caso": "OTRO_CASO",

    # Aqui estan las palabras para los ciclos.
    "para": "PARA",
    "mientras": "MIENTRAS",
    "repetir": "REPETIR",
    "detener": "DETENER",
    "seguir": "SEGUIR",
    "en": "EN",

    # Operadores que se escriben como palabras.
    "y": "Y",
    "o": "O",
    "negar": "NEGAR",
    "div": "DIV_ENTERA",

    # Estas palabras las agregue para otras funciones del lenguaje.
    "vigilar": "VIGILAR",
    "proteger": "PROTEGER",
    "atrapar": "ATRAPAR",
    "lanzar": "LANZAR",
    "finalmente": "FINALMENTE",

    # Palabras que pueden utilizarse para trabajar con clases y objetos.
    "clase": "CLASE",
    "crear": "CREAR",
    "este": "ESTE",
    "iniciar": "INICIAR",
    "publico": "PUBLICO",
    "privado": "PRIVADO",
    "hereda": "HEREDA",

    # Por ultimo dejo las palabras para modulos y estructuras.
    "usar": "USAR",
    "modulo": "MODULO",
    "estructura": "ESTRUCTURA",
    "enumeracion": "ENUMERACION",
}


# Esta lista contiene los tokens que puede encontrar el analizador.
# Al final tambien agrego los tokens de las palabras reservadas.
tokens = [
    "IDENTIFICADOR",
    "NUMERO",
    "CADENA",
    "CARACTER",
    "SI_PASO",
    "NO_PASO",

    # Tokens para las operaciones matematicas.
    "SUMA",
    "RESTA",
    "MULTIPLICACION",
    "DIVISION",
    "RESIDUO",
    "POTENCIA",

    # Tokens para comparar valores.
    "IGUAL",
    "DIFERENTE",
    "MAYOR",
    "MENOR",
    "MAYORIGUAL",
    "MENORIGUAL",

    # Estos se usan cuando se asignan o actualizan valores.
    "ASIGNAR",
    "MASIGUAL",
    "MENOSIGUAL",
    "PORIGUAL",
    "DIVIGUAL",

    # Simbolos que ayudan a separar las partes del codigo.
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


# Aqui defino como se escribe cada operador.
# Uso expresiones regulares para que PLY pueda reconocerlos.
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

# Tambien defino los signos que aparecen en las instrucciones.
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


# Los espacios y tabulaciones no necesitan convertirse en tokens.
t_ignore = " \t"


# En JARVIS uso "si paso" y "no paso" como valores logicos.
# Los reconozco completos antes de revisar los identificadores.
def t_SI_PASO(t):
    r"si[ \t]+paso\b"
    return t


def t_NO_PASO(t):
    r"no[ \t]+paso\b"
    return t


# Los comentarios de una linea empiezan con // y no generan tokens.
def t_COMENTARIO_LINEA(t):
    r"//[^\n]*"
    pass


# Para comentarios de varias lineas uso /* y */.
# Tambien cuento sus saltos de linea para ubicar posibles errores.
def t_COMENTARIO_BLOQUE(t):
    r"/\*[\s\S]*?\*/"
    t.lexer.lineno += t.value.count("\n")


# Las cadenas son textos escritos entre comillas dobles.
def t_CADENA(t):
    r'"([^"\\\n]|\\.)*"'
    return t


# Los caracteres van entre comillas simples.
def t_CARACTER(t):
    r"'([^'\\\n]|\\.)'"
    return t


# Aqui reconozco los numeros enteros y decimales.
def t_NUMERO(t):
    r"\d+(\.\d+)?"

    # Si tiene un punto lo guardo como decimal.
    if "." in t.value:
        t.value = float(t.value)
    else:
        t.value = int(t.value)

    return t


# Los identificadores son nombres de variables, acciones o sistemas.
def t_IDENTIFICADOR(t):
    r"[a-zA-Z_][a-zA-Z0-9_]*"

    # Primero compruebo si la palabra es reservada.
    # Si no aparece en el diccionario, queda como identificador.
    t.type = reservadas.get(
        t.value, "IDENTIFICADOR"
    )

    return t


# Cada salto de linea aumenta el contador del lexer.
def t_newline(t):
    r"\n+"
    t.lexer.lineno += len(t.value)


# Si encuentro un caracter desconocido, muestro donde ocurrio.
# Despues avanzo un caracter para continuar con el analisis.
def t_error(t):
    print(
        f"Error lexico en la linea {t.lineno}: "
        f"caracter no reconocido '{t.value[0]}'"
    )
    t.lexer.skip(1)


# Con todas las reglas anteriores creo el analizador de PLY.
lexer = lex.lex()


# Este codigo me sirve para probar los tokens de JARVIS.
# Incluye variables, condiciones, ciclos y llamadas a acciones.
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


# Esta parte solo se ejecuta cuando pruebo lexer.py directamente.
if __name__ == "__main__":

    # Le paso el programa de prueba al analizador.
    lexer.input(codigo)

    print("========== TOKENS DE JARVIS ==========")

    # Recorro los tokens para ver que reconoce cada palabra o simbolo.
    for token in lexer:
        print(f"{token.type:20} | {token.value}")

    print("========== FIN DEL ANALISIS ==========")
