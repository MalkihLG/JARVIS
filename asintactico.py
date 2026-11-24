"""Analizador sintactico del lenguaje JARVIS mediante PLY.

Se comprueba la estructura del programa y se construye un AST.
Las reglas semanticas y la ejecucion corresponden a otros modulos.
"""

import ast as python_ast
import ply.yacc as yacc

from alexico import lexer, tokens



# Se establece la prioridad de las expresiones del lenguaje.
precedence = (
    ("left", "O"),
    ("left", "Y"),
    (
        "nonassoc",
        "IGUAL", "DIFERENTE",
        "MAYOR", "MENOR",
        "MAYORIGUAL", "MENORIGUAL"
    ),
    ("left", "SUMA", "RESTA"),
    (
        "left",
        "MULTIPLICACION",
        "DIVISION",
        "DIV_ENTERA",
        "RESIDUO"
    ),
    ("right", "NEGAR", "UMENOS", "UMAS"),
    ("right", "POTENCIA"),
    ("left", "PUNTO", "PARIZQ", "CORCHETEIZQ"),
)


# Se organiza el contenido del sistema y se conserva el AST original.
def p_programa(p):
    "programa : SISTEMA IDENTIFICADOR LLAVEIZQ elementos LLAVEDER"

    elementos = p[4]

    principales = [
        elemento
        for elemento in elementos
        if elemento["tipo"] == "mision"
        and elemento["nombre"] == "principal"
    ]

    if len(principales) != 1:
        raise SyntaxError(
            "JARVIS requiere exactamente una mision principal"
        )

    acciones = [
        elemento
        for elemento in elementos
        if elemento["tipo"] == "accion"
    ]

    p[0] = {
        "tipo": "sistema",
        "nombre": p[2],
        "acciones": acciones,
        "mision": principales[0],
        "misiones": [
            elemento for elemento in elementos
            if elemento["tipo"] == "mision"
            and elemento["nombre"] != "principal"
        ],
        "globales": [
            elemento for elemento in elementos
            if elemento["tipo"] == "variable"
        ],
        "vigilancias": [
            elemento for elemento in elementos
            if elemento["tipo"] == "vigilar"
        ],
        "definiciones": [
            elemento for elemento in elementos
            if elemento["tipo"] in (
                "clase",
                "modulo",
                "estructura",
                "enumeracion",
                "usar"
            )
        ],
        "elementos": elementos,
    }


# Se agrupan los elementos que forman parte del sistema.
def p_elementos(p):
    """
    elementos : elementos elemento
              | vacio
    """

    p[0] = p[1] + [p[2]] if len(p) == 3 else []


# Se identifican las declaraciones permitidas a nivel de sistema.
def p_elemento(p):
    """
    elemento : accion
             | mision
             | declaracion PUNTOYCOMA
             | vigilancia
             | clase
             | modulo
             | estructura
             | enumeracion
             | importar
    """

    p[0] = p[1]


# Se reconocen la mision principal y las misiones secundarias.
def p_mision(p):
    """
    mision : MISION PRINCIPAL bloque
           | MISION IDENTIFICADOR bloque
    """

    p[0] = {
        "tipo": "mision",
        "nombre": p[2],
        "instrucciones": p[3]
    }


# Se reconocen acciones con parametros y retorno opcionales.
def p_accion(p):
    """
    accion : ACCION nombre_accion PARIZQ parametros_opt PARDER retorno_opt bloque
    """

    p[0] = {
        "tipo": "accion",
        "nombre": p[2],
        "parametros": p[4],
        "retorno": p[6],
        "instrucciones": p[7]
    }


# Se permite utilizar un identificador o iniciar como nombre de accion.
def p_nombre_accion(p):
    """
    nombre_accion : IDENTIFICADOR
                  | INICIAR
    """

    p[0] = p[1]


# Se reconoce el tipo de retorno declarado por una accion.
def p_retorno_opt(p):
    """
    retorno_opt : FLECHA tipo
                | vacio
    """

    p[0] = p[2] if len(p) == 3 else None


# Se permite declarar acciones con o sin parametros.
def p_parametros_opt(p):
    """
    parametros_opt : parametros
                   | vacio
    """

    p[0] = p[1]


# Se agrupan los parametros de una accion.
def p_parametros(p):
    """
    parametros : parametros COMA parametro
               | parametro
    """

    p[0] = p[1] + [p[3]] if len(p) == 4 else [p[1]]


# Se almacena el nombre y el tipo de cada parametro.
def p_parametro(p):
    """
    parametro : IDENTIFICADOR DOSPUNTOS tipo
    """

    p[0] = {
        "nombre": p[1],
        "tipo": p[3]
    }


# Se reconocen los tipos de datos basicos de JARVIS.
def p_tipo_basico(p):
    """
    tipo : ENTERO
         | DECIMAL
         | CADENITA
         | LOGICO
         | CARACTER_TIPO
         | VACIO
    """

    p[0] = p[1]


# Se reconocen los tipos personalizados definidos por el programa.
def p_tipo_personalizado(p):
    """
    tipo : IDENTIFICADOR
    """

    p[0] = {
        "tipo": "personalizado",
        "nombre": p[1]
    }


# Se reconocen las listas con un tipo de elemento.
def p_tipo_lista(p):
    """
    tipo : LISTA CORCHETEIZQ tipo CORCHETEDER
    """

    p[0] = {
        "tipo": "lista",
        "elemento": p[3]
    }


# Se reconocen los mapas con tipos para claves y valores.
def p_tipo_mapa(p):
    """
    tipo : MAPA CORCHETEIZQ tipo COMA tipo CORCHETEDER
    """

    p[0] = {
        "tipo": "mapa",
        "clave": p[3],
        "valor": p[5]
    }


# Se agrupan las instrucciones delimitadas por llaves.
def p_bloque(p):
    """
    bloque : LLAVEIZQ instrucciones LLAVEDER
    """

    p[0] = p[2]


# Se permite utilizar bloques vacios o con varias instrucciones.
def p_instrucciones(p):
    """
    instrucciones : instrucciones instruccion
                  | vacio
    """

    p[0] = p[1] + [p[2]] if len(p) == 3 else []


# Se representa una produccion vacia.
def p_vacio(p):
    """
    vacio :
    """

    p[0] = []


# Se reconocen variables normales, constantes y variables observables.
def p_declaracion(p):
    """
    declaracion : declarador IDENTIFICADOR anotacion_opt inicializacion_opt
    """

    p[0] = {
        "tipo": "variable",
        "nombre": p[2],
        "dato": p[3],
        "valor": p[4],
        "clase": p[1]
    }


# Se identifica la clase de declaracion.
def p_declarador(p):
    """
    declarador : VAR
               | FIJO
               | ESTADO
    """

    p[0] = p[1]


# Se reconoce la declaracion opcional de un tipo.
def p_anotacion_opt(p):
    """
    anotacion_opt : DOSPUNTOS tipo
                  | vacio
    """

    p[0] = p[2] if len(p) == 3 else None


# Se reconoce la inicializacion opcional de una variable.
def p_inicializacion_opt(p):
    """
    inicializacion_opt : ASIGNAR expresion
                       | vacio
    """

    p[0] = p[2] if len(p) == 3 else None


# Se permiten asignaciones simples y actualizaciones de valores.
def p_asignacion(p):
    """
    asignacion : asignable operador_asignacion expresion
    """

    objetivo = p[1]

    p[0] = {
        "tipo": "asignacion",
        "nombre": (
            objetivo.get("nombre")
            if objetivo["tipo"] == "identificador"
            else None
        ),
        "objetivo": objetivo,
        "operador": p[2],
        "valor": p[3]
    }


# Se reconocen los operadores de asignacion.
def p_operador_asignacion(p):
    """
    operador_asignacion : ASIGNAR
                        | MASIGUAL
                        | MENOSIGUAL
                        | PORIGUAL
                        | DIVIGUAL
    """

    p[0] = p[1]


# Se reconocen las variables y la referencia al objeto actual.
def p_asignable_identificador(p):
    """
    asignable : IDENTIFICADOR
              | ESTE
    """

    if p.slice[1].type == "IDENTIFICADOR":

        p[0] = {
            "tipo": "identificador",
            "nombre": p[1]
        }

    else:

        p[0] = {
            "tipo": "este"
        }


# Se reconoce el acceso a elementos por indice.
def p_asignable_indice(p):
    """
    asignable : asignable CORCHETEIZQ expresion CORCHETEDER
    """

    p[0] = {
        "tipo": "indice",
        "objeto": p[1],
        "indice": p[3]
    }


# Se reconoce el acceso a atributos de un objeto.
def p_asignable_atributo(p):
    """
    asignable : asignable PUNTO IDENTIFICADOR
    """

    p[0] = {
        "tipo": "atributo",
        "objeto": p[1],
        "nombre": p[3]
    }


# Se reconocen las llamadas independientes a acciones y metodos.
# Se permiten llamadas como objeto.metodo(); y modulo.accion();
# Se conserva la estructura del AST utilizada por el ejecutor.
def p_instruccion_llamada_independiente(p):
    """
    instruccion : asignable PARIZQ argumentos_opt PARDER PUNTOYCOMA
    """

    destino = p[1]

    # Se distingue una accion global de un metodo de objeto.
    if destino["tipo"] == "identificador":
        nombre = destino["nombre"]
    else:
        nombre = None

    # Se construye un nodo compatible con el analizador
    # semantico, el ejecutor y el generador del AST.
    p[0] = {
        "tipo": "llamada",
        "nombre": nombre,
        "objetivo": destino,
        "argumentos": p[3]
    }

# Se reconocen declaraciones, asignaciones y expresiones independientes.
def p_instruccion_simple(p):
    """
    instruccion : declaracion PUNTOYCOMA
                | asignacion PUNTOYCOMA
                | expresion PUNTOYCOMA
    """

    p[0] = p[1]


# Se reconocen las instrucciones de salida y registro de eventos.
def p_instruccion_salida(p):
    """
    instruccion : salida PARIZQ argumentos_opt PARDER PUNTOYCOMA
    """

    nombre = p[1]
    argumentos = p[3]

    if nombre == "imprimir":

        p[0] = {
            "tipo": "imprimir",
            "mensaje": argumentos[0] if argumentos else "",
            "argumentos": argumentos
        }

    else:

        p[0] = {
            "tipo": nombre,
            "argumentos": argumentos
        }


# Se identifican las instrucciones de salida disponibles.
def p_salida(p):
    """
    salida : IMPRIMIR
           | ALERTA
           | REGISTRAR
    """

    p[0] = p[1]


# Se reconoce la estructura principal de una condicion.
def p_instruccion_si(p):
    """
    instruccion : SI PARIZQ expresion PARDER bloque opcion_sino
    """

    p[0] = {
        "tipo": "si",
        "condicion": p[3],
        "instrucciones_si": p[5],
        "instrucciones_sino": p[6]
    }


# Se reconoce sinosi como una alternativa de la condicion principal.
# Se conserva la estructura anidada para facilitar la compatibilidad.
def p_opcion_sino_sinosi(p):
    """
    opcion_sino : SINOSI PARIZQ expresion PARDER bloque opcion_sino
    """

    p[0] = [
        {
            "tipo": "si",
            "variante": "sinosi",
            "condicion": p[3],
            "instrucciones_si": p[5],
            "instrucciones_sino": p[6]
        }
    ]


# Se reconocen las instrucciones del bloque sino.
def p_opcion_sino(p):
    """
    opcion_sino : SINO bloque
    """

    p[0] = p[2]


# Se permite omitir el bloque sino.
def p_opcion_sino_vacia(p):
    """
    opcion_sino : vacio
    """

    p[0] = []


# Se reconoce la seleccion entre varios casos.
def p_instruccion_segun(p):
    """
    instruccion : SEGUN PARIZQ expresion PARDER LLAVEIZQ casos otro_caso_opt LLAVEDER
    """

    p[0] = {
        "tipo": "segun",
        "valor": p[3],
        "casos": p[6],
        "otro_caso": p[7]
    }


# Se agrupan los casos de una seleccion.
def p_casos(p):
    """
    casos : casos caso
          | vacio
    """

    p[0] = p[1] + [p[2]] if len(p) == 3 else []


# Se reconoce un caso y su bloque de instrucciones.
def p_caso(p):
    """
    caso : CASO expresion DOSPUNTOS bloque
    """

    p[0] = {
        "valor": p[2],
        "instrucciones": p[4]
    }


# Se reconoce la alternativa utilizada cuando ningun caso coincide.
def p_otro_caso_opt(p):
    """
    otro_caso_opt : OTRO_CASO DOSPUNTOS bloque
                  | vacio
    """

    p[0] = p[3] if len(p) == 4 else []


# Se reconoce la repeticion de un bloque un numero determinado de veces.
def p_instruccion_repetir(p):
    """
    instruccion : REPETIR PARIZQ expresion PARDER bloque
    """

    p[0] = {
        "tipo": "repetir",
        "cantidad": p[3],
        "instrucciones": p[5]
    }


# Se reconoce el ciclo que depende de una condicion.
def p_instruccion_mientras(p):
    """
    instruccion : MIENTRAS PARIZQ expresion PARDER bloque
    """

    p[0] = {
        "tipo": "mientras",
        "condicion": p[3],
        "instrucciones": p[5]
    }


# Se reconoce un ciclo para con declaracion inicial.
def p_instruccion_para_var(p):
    """
    instruccion : PARA PARIZQ VAR IDENTIFICADOR cola_var_para PARDER bloque
    """

    cabecera = p[5]

    if cabecera["tipo"] == "para_en":

        p[0] = {
            "tipo": "para_en",
            "iterador": {
                "nombre": p[4],
                "declarar": True
            },
            "coleccion": cabecera["coleccion"],
            "instrucciones": p[7]
        }

    else:

        inicio = {
            "tipo": "variable",
            "clase": "var",
            "nombre": p[4],
            "dato": cabecera["dato"],
            "valor": cabecera["valor"]
        }

        p[0] = {
            "tipo": "para",
            "inicio": inicio,
            "condicion": cabecera["condicion"],
            "cambio": cabecera["cambio"],
            "instrucciones": p[7]
        }


# Se reconoce el recorrido de colecciones con una variable nueva.
def p_cola_var_para_iterador(p):
    """
    cola_var_para : EN expresion
    """

    p[0] = {
        "tipo": "para_en",
        "coleccion": p[2]
    }


# Se reconoce la inicializacion de un contador.
def p_cola_var_para_contador(p):
    """
    cola_var_para : anotacion_opt inicializacion_opt PUNTOYCOMA expresion PUNTOYCOMA parte_para
    """

    p[0] = {
        "tipo": "para",
        "dato": p[1],
        "valor": p[2],
        "condicion": p[4],
        "cambio": p[6]
    }


# Se reconocen ciclos para que utilizan una variable existente.
def p_instruccion_para_id(p):
    """
    instruccion : PARA PARIZQ IDENTIFICADOR cola_id_para PARDER bloque
    """

    cabecera = p[4]

    if cabecera["tipo"] == "para_en":

        p[0] = {
            "tipo": "para_en",
            "iterador": {
                "nombre": p[3],
                "declarar": False
            },
            "coleccion": cabecera["coleccion"],
            "instrucciones": p[6]
        }

    else:

        inicio = {
            "tipo": "asignacion",
            "nombre": p[3],
            "objetivo": {
                "tipo": "identificador",
                "nombre": p[3]
            },
            "operador": cabecera["operador"],
            "valor": cabecera["valor"]
        }

        p[0] = {
            "tipo": "para",
            "inicio": inicio,
            "condicion": cabecera["condicion"],
            "cambio": cabecera["cambio"],
            "instrucciones": p[6]
        }


# Se reconoce el recorrido de una coleccion existente.
def p_cola_id_para_iterador(p):
    """
    cola_id_para : EN expresion
    """

    p[0] = {
        "tipo": "para_en",
        "coleccion": p[2]
    }


# Se reconocen las asignaciones iniciales de un ciclo con contador.
def p_cola_id_para_contador(p):
    """
    cola_id_para : operador_asignacion expresion PUNTOYCOMA expresion PUNTOYCOMA parte_para
    """

    p[0] = {
        "tipo": "para",
        "operador": p[1],
        "valor": p[2],
        "condicion": p[4],
        "cambio": p[6]
    }


# Se permite utilizar un ciclo para sin inicializacion.
def p_instruccion_para_vacio(p):
    """
    instruccion : PARA PARIZQ PUNTOYCOMA expresion PUNTOYCOMA parte_para PARDER bloque
    """

    p[0] = {
        "tipo": "para",
        "inicio": None,
        "condicion": p[4],
        "cambio": p[6],
        "instrucciones": p[8]
    }


# Se reconoce el cambio que se realiza al terminar cada iteracion.
def p_parte_para(p):
    """
    parte_para : asignacion
               | vacio
    """

    p[0] = p[1] if p[1] != [] else None


# Se reconocen las instrucciones para controlar los ciclos.
def p_instruccion_salto(p):
    """
    instruccion : DETENER PUNTOYCOMA
                | SEGUIR PUNTOYCOMA
    """

    p[0] = {
        "tipo": p[1]
    }


# Se reconoce la instruccion que devuelve un resultado.
def p_instruccion_devolver(p):
    """
    instruccion : DEVOLVER valor_opt PUNTOYCOMA
    """

    p[0] = {
        "tipo": "devolver",
        "valor": p[2]
    }


# Se reconoce un valor opcional.
def p_valor_opt(p):
    """
    valor_opt : expresion
              | vacio
    """

    p[0] = p[1] if p[1] != [] else None


# Se reconoce la ejecucion de una mision secundaria.
def p_instruccion_ejecutar(p):
    """
    instruccion : EJECUTAR IDENTIFICADOR PUNTOYCOMA
    """

    p[0] = {
        "tipo": "ejecutar",
        "nombre": p[2]
    }


# Se reconocen los bloques utilizados para manejar errores.
def p_instruccion_proteger(p):
    """
    instruccion : PROTEGER bloque atrapar_opt finalmente_opt
    """

    p[0] = {
        "tipo": "proteger",
        "instrucciones": p[2],
        "atrapar": p[3],
        "finalmente": p[4]
    }


# Se reconoce un bloque de captura de errores.
def p_atrapar_opt(p):
    """
    atrapar_opt : ATRAPAR PARIZQ IDENTIFICADOR PARDER bloque
                | vacio
    """

    if len(p) == 6:

        p[0] = {
            "nombre": p[3],
            "instrucciones": p[5]
        }

    else:

        p[0] = None


# Se reconoce el bloque que se ejecuta al finalizar la proteccion.
def p_finalmente_opt(p):
    """
    finalmente_opt : FINALMENTE bloque
                   | vacio
    """

    p[0] = p[2] if len(p) == 3 else []


# Se reconoce la instruccion que genera un error controlado.
def p_instruccion_lanzar(p):
    """
    instruccion : LANZAR expresion PUNTOYCOMA
    """

    p[0] = {
        "tipo": "lanzar",
        "valor": p[2]
    }


# Se reconoce una vigilancia reactiva sobre una condicion.
def p_vigilancia(p):
    """
    vigilancia : VIGILAR PARIZQ expresion PARDER bloque
    """

    p[0] = {
        "tipo": "vigilar",
        "condicion": p[3],
        "instrucciones": p[5]
    }


# Se permite utilizar vigilancia dentro de las instrucciones.
def p_instruccion_vigilar(p):
    """
    instruccion : vigilancia
    """

    p[0] = p[1]


# Se reconoce una clase y su posible herencia.
def p_clase(p):
    """
    clase : CLASE IDENTIFICADOR herencia_opt LLAVEIZQ miembros LLAVEDER
    """

    p[0] = {
        "tipo": "clase",
        "nombre": p[2],
        "hereda": p[3],
        "miembros": p[5]
    }


# Se reconoce la clase de la que se heredan atributos y acciones.
def p_herencia_opt(p):
    """
    herencia_opt : HEREDA IDENTIFICADOR
                 | vacio
    """

    p[0] = p[2] if len(p) == 3 else None


# Se agrupan los miembros declarados dentro de una clase.
def p_miembros(p):
    """
    miembros : miembros miembro
             | vacio
    """

    p[0] = p[1] + [p[2]] if len(p) == 3 else []


# Se reconocen los atributos y las acciones de una clase.
def p_miembro(p):
    """
    miembro : declaracion PUNTOYCOMA
            | accion
            | visibilidad declaracion PUNTOYCOMA
            | visibilidad accion
    """

    if p.slice[1].type == "visibilidad":

        elemento = p[2]
        elemento["visibilidad"] = p[1]

    else:

        elemento = p[1]

    p[0] = elemento


# Se reconoce la visibilidad de los miembros de una clase.
def p_visibilidad(p):
    """
    visibilidad : PUBLICO
                | PRIVADO
    """

    p[0] = p[1]


# Se reconoce la declaracion de una estructura.
def p_estructura(p):
    """
    estructura : ESTRUCTURA IDENTIFICADOR LLAVEIZQ campos LLAVEDER
    """

    p[0] = {
        "tipo": "estructura",
        "nombre": p[2],
        "campos": p[4]
    }


# Se agrupan los campos que pertenecen a una estructura.
def p_campos(p):
    """
    campos : campos campo
           | vacio
    """

    p[0] = p[1] + [p[2]] if len(p) == 3 else []


# Se reconoce el nombre y tipo de cada campo.
def p_campo(p):
    """
    campo : IDENTIFICADOR DOSPUNTOS tipo PUNTOYCOMA
    """

    p[0] = {
        "nombre": p[1],
        "tipo": p[3]
    }


# Se reconoce una enumeracion.
def p_enumeracion(p):
    """
    enumeracion : ENUMERACION IDENTIFICADOR LLAVEIZQ nombres_opt LLAVEDER
    """

    p[0] = {
        "tipo": "enumeracion",
        "nombre": p[2],
        "valores": p[4]
    }


# Se permite declarar una enumeracion vacia.
def p_nombres_opt(p):
    """
    nombres_opt : nombres
                | vacio
    """

    p[0] = p[1]


# Se agrupan los nombres de una enumeracion.
def p_nombres(p):
    """
    nombres : nombres COMA IDENTIFICADOR
            | IDENTIFICADOR
    """

    p[0] = p[1] + [p[3]] if len(p) == 4 else [p[1]]


# Se reconoce la definicion de un modulo.
def p_modulo(p):
    """
    modulo : MODULO IDENTIFICADOR LLAVEIZQ elementos LLAVEDER
    """

    p[0] = {
        "tipo": "modulo",
        "nombre": p[2],
        "elementos": p[4]
    }


# Se reconoce la importacion de un modulo.
def p_importar(p):
    """
    importar : USAR ruta PUNTOYCOMA
    """

    p[0] = {
        "tipo": "usar",
        "ruta": p[2]
    }


# Se reconoce una ruta formada por nombres separados por puntos.
def p_ruta(p):
    """
    ruta : ruta PUNTO IDENTIFICADOR
         | IDENTIFICADOR
    """

    p[0] = (
        p[1] + "." + p[3]
        if len(p) == 4
        else p[1]
    )


# Se reconocen operaciones matematicas, comparaciones y operadores logicos.
def p_expresion_binaria(p):
    """
    expresion : expresion SUMA expresion
              | expresion RESTA expresion
              | expresion MULTIPLICACION expresion
              | expresion DIVISION expresion
              | expresion DIV_ENTERA expresion
              | expresion RESIDUO expresion
              | expresion POTENCIA expresion
              | expresion IGUAL expresion
              | expresion DIFERENTE expresion
              | expresion MAYOR expresion
              | expresion MENOR expresion
              | expresion MAYORIGUAL expresion
              | expresion MENORIGUAL expresion
              | expresion Y expresion
              | expresion O expresion
    """

    operador = p[2]
    token = p.slice[2].type

    if token in ("Y", "O"):

        tipo = "logica"

    elif token in (
        "IGUAL",
        "DIFERENTE",
        "MAYOR",
        "MENOR",
        "MAYORIGUAL",
        "MENORIGUAL"
    ):

        tipo = "comparacion"

    else:

        tipo = "operacion"

    p[0] = {
        "tipo": tipo,
        "operador": operador,
        "izquierda": p[1],
        "derecha": p[3]
    }


# Se reconocen los operadores de un solo operando.
def p_expresion_unaria(p):
    """
    expresion : NEGAR expresion
              | RESTA expresion %prec UMENOS
              | SUMA expresion %prec UMAS
    """

    p[0] = {
        "tipo": "unario",
        "operador": p[1],
        "valor": p[2]
    }


# Se permite agrupar expresiones mediante parentesis.
def p_expresion_parentesis(p):
    """
    expresion : PARIZQ expresion PARDER
    """

    p[0] = p[2]


# Se reconocen los valores literales y los identificadores.
# Las cadenas y los caracteres se representan por separado.
def p_expresion_literal(p):
    """
    expresion : NUMERO
              | SI_PASO
              | NO_PASO
              | CADENA
              | CARACTER
              | NADA
              | IDENTIFICADOR
              | ESTE
    """

    tipo = p.slice[1].type

    if tipo == "IDENTIFICADOR":

        p[0] = {
            "tipo": "identificador",
            "nombre": p[1]
        }

    elif tipo == "ESTE":

        p[0] = {
            "tipo": "este"
        }

    elif tipo in ("CADENA", "CARACTER"):

        try:

            texto = python_ast.literal_eval(p[1])

        except (SyntaxError, ValueError):

            raise SyntaxError(
                f"Literal invalido en linea {p.lineno(1)}"
            )

        p[0] = {
            "tipo": (
                "cadena"
                if tipo == "CADENA"
                else "caracter"
            ),
            "valor": texto
        }

    elif tipo == "NADA":

        p[0] = {
            "tipo": "nada",
            "valor": None
        }

    else:

        p[0] = p[1]


# Se reconoce la creacion de una lista.
def p_expresion_lista(p):
    """
    expresion : CORCHETEIZQ argumentos_opt CORCHETEDER
    """

    p[0] = {
        "tipo": "lista",
        "elementos": p[2]
    }


# Se reconoce la creacion de un mapa.
def p_expresion_mapa(p):
    """
    expresion : LLAVEIZQ pares_opt LLAVEDER
    """

    p[0] = {
        "tipo": "mapa",
        "pares": p[2]
    }


# Se permite crear un mapa sin elementos.
def p_pares_opt(p):
    """
    pares_opt : pares
              | vacio
    """

    p[0] = p[1]


# Se agrupan los pares de clave y valor de un mapa.
def p_pares(p):
    """
    pares : pares COMA par
          | par
    """

    p[0] = p[1] + [p[3]] if len(p) == 4 else [p[1]]


# Se reconoce un par formado por clave y valor.
def p_par(p):
    """
    par : expresion DOSPUNTOS expresion
    """

    p[0] = {
        "clave": p[1],
        "valor": p[3]
    }


# Se reconoce el acceso a un elemento mediante un indice.
def p_expresion_indice(p):
    """
    expresion : expresion CORCHETEIZQ expresion CORCHETEDER
    """

    p[0] = {
        "tipo": "indice",
        "objeto": p[1],
        "indice": p[3]
    }


# Se reconoce la consulta de un atributo de un objeto.
def p_expresion_atributo(p):
    """
    expresion : expresion PUNTO IDENTIFICADOR
    """

    p[0] = {
        "tipo": "atributo",
        "objeto": p[1],
        "nombre": p[3]
    }


# Se reconocen las llamadas a acciones y funciones.
def p_expresion_llamada(p):
    """
    expresion : expresion PARIZQ argumentos_opt PARDER
    """

    destino = p[1]

    if (
        isinstance(destino, dict)
        and destino.get("tipo") == "identificador"
    ):

        nombre = destino.get("nombre")

    else:

        nombre = None

    p[0] = {
        "tipo": "llamada",
        "nombre": nombre,
        "objetivo": destino,
        "argumentos": p[3]
    }


# Se reconocen las funciones especiales preguntar y checar.
def p_expresion_intrinseca(p):
    """
    expresion : intrinseca PARIZQ argumentos_opt PARDER
    """

    p[0] = {
        "tipo": "llamada",
        "nombre": p[1],
        "argumentos": p[3],
        "integrada": True
    }


# Se agrupan las funciones especiales disponibles como palabras reservadas.
def p_intrinseca(p):
    """
    intrinseca : PREGUNTAR
               | CHECAR
    """

    p[0] = p[1]


# Se reconoce la creacion de una instancia de una clase.
def p_expresion_crear(p):
    """
    expresion : CREAR IDENTIFICADOR PARIZQ argumentos_opt PARDER
    """

    p[0] = {
        "tipo": "crear",
        "clase": p[2],
        "argumentos": p[4]
    }


# Se permiten llamadas con y sin argumentos.
def p_argumentos_opt(p):
    """
    argumentos_opt : argumentos
                   | vacio
    """

    p[0] = p[1]


# Se agrupan los argumentos de una llamada.
def p_argumentos(p):
    """
    argumentos : argumentos COMA expresion
               | expresion
    """

    p[0] = p[1] + [p[3]] if len(p) == 4 else [p[1]]


# Se comunica la ubicacion del primer error sintactico encontrado.
def p_error(p):

    if p is not None:

        raise SyntaxError(
            f"Error sintactico en linea {p.lineno}: "
            f"token inesperado '{p.value}' ({p.type})"
        )

    raise SyntaxError(
        "Error sintactico: fin inesperado del programa"
    )


# Se construye el analizador sintactico mediante PLY.
# Se conserva el nombre parser para mantener las importaciones existentes.
parser = yacc.yacc(
    start="programa",
    debug=False,
    write_tables=False
)


# Se genera una representacion legible de una expresion.
def mostrar_valor(valor):

    if isinstance(valor, dict):

        tipo = valor.get("tipo")

        if tipo == "identificador":

            return valor["nombre"]

        if tipo in ("cadena", "caracter"):

            return repr(valor["valor"])

        if tipo in ("operacion", "comparacion", "logica"):

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

        if tipo == "unario":

            return (
                f"({valor['operador']} "
                f"{mostrar_valor(valor['valor'])})"
            )

        if tipo == "llamada":

            argumentos = ", ".join(
                mostrar_valor(argumento)
                for argumento in valor["argumentos"]
            )

            return (
                f"{valor.get('nombre') or 'llamada'}"
                f"({argumentos})"
            )

        if tipo == "lista":

            elementos = ", ".join(
                mostrar_valor(elemento)
                for elemento in valor["elementos"]
            )

            return f"[{elementos}]"

        if tipo == "mapa":

            pares = ", ".join(
                f"{mostrar_valor(par['clave'])}: "
                f"{mostrar_valor(par['valor'])}"
                for par in valor["pares"]
            )

            return "{" + pares + "}"

        return str(valor)

    return str(valor)


# Se recorren y muestran las instrucciones del AST.
def mostrar_instruccion(instruccion, nivel=0):

    espacio = "    " * nivel
    tipo = instruccion["tipo"]

    if tipo == "variable":

        print(
            f"{espacio}{instruccion['clase']} "
            f"{instruccion['nombre']}: "
            f"{instruccion['dato']} = "
            f"{mostrar_valor(instruccion['valor'])}"
        )

    elif tipo == "asignacion":

        objetivo = (
            instruccion.get("nombre")
            or mostrar_valor(instruccion["objetivo"])
        )

        print(
            f"{espacio}Asignacion: "
            f"{objetivo} "
            f"{instruccion['operador']} "
            f"{mostrar_valor(instruccion['valor'])}"
        )

    elif tipo == "imprimir":

        argumentos = ", ".join(
            mostrar_valor(argumento)
            for argumento in instruccion["argumentos"]
        )

        print(
            f"{espacio}Imprimir: {argumentos}"
        )

    elif tipo == "si":

        print(
            f"{espacio}SI "
            f"({mostrar_valor(instruccion['condicion'])})"
        )

        for elemento in instruccion["instrucciones_si"]:

            mostrar_instruccion(
                elemento,
                nivel + 1
            )

        if instruccion["instrucciones_sino"]:

            print(f"{espacio}SINO:")

            for elemento in instruccion["instrucciones_sino"]:

                mostrar_instruccion(
                    elemento,
                    nivel + 1
                )

    elif tipo in (
        "mientras",
        "repetir",
        "vigilar",
        "para",
        "para_en"
    ):

        print(
            f"{espacio}{tipo.upper()}"
        )

        for elemento in instruccion["instrucciones"]:

            mostrar_instruccion(
                elemento,
                nivel + 1
            )

    else:

        print(
            f"{espacio}{tipo}: {instruccion}"
        )


# Se conserva el programa de ejemplo original de JARVIS.
# Se utiliza para comprobar las reglas y mostrar codigo al abrir el editor.
codigo = '''
sistema StarkLab {

    accion activarArmadura() {
        imprimir("Armadura activada");
    }

    accion usarPropulsor(consumo: entero) {
        imprimir("Propulsor activado");
        imprimir(consumo);
    }

    accion presentarHeroe(nombre: cadenita, energia: entero) {
        imprimir("Datos del superheroe");
        imprimir("Nombre:");
        imprimir(nombre);
        imprimir("Energia:");
        imprimir(energia);
    }

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

        activarArmadura();
        usarPropulsor(25);
        presentarHeroe(heroe, energia);

        imprimir("resultado:");
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

        var contador: entero = 3;

        mientras (contador > 0) {
            imprimir(contador);
            contador -= 1;
        }
    }
}
'''


# Se permite ejecutar el analizador directamente para comprobar la sintaxis.
if __name__ == "__main__":

    lexer.lineno = 1

    try:

        # Se construye el AST del programa de ejemplo.
        arbol = parser.parse(
            codigo,
            lexer=lexer
        )

        print("========== JARVIS ==========")
        print("Analisis sintactico correcto")
        print("Sistema:", arbol["nombre"])
        print("Mision:", arbol["mision"]["nombre"])

        # Se muestran las acciones declaradas.
        for accion in arbol["acciones"]:

            print(
                "Accion:",
                accion["nombre"]
            )

            for instruccion in accion["instrucciones"]:

                mostrar_instruccion(
                    instruccion,
                    1
                )

        # Se muestran las instrucciones de la mision principal.
        print("\nInstrucciones de la mision principal:")

        for instruccion in arbol["mision"]["instrucciones"]:

            mostrar_instruccion(
                instruccion,
                1
            )

    except SyntaxError as error:

        print("========== ERROR JARVIS ==========")
        print(error)

