"""Se verifican tipos, ambitos, constantes, acciones, estructuras, clases,
colecciones, modulos y expresiones. No se ejecutan instrucciones aqui.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator


class ErrorSemantico(Exception):
    """Se informa una infraccion semantica del lenguaje."""


tabla_simbolos: dict[str, dict[str, Any]] = {}
tabla_acciones: dict[str, dict[str, Any]] = {}

NUMERICOS = ("entero", "decimal")

BASICOS = (
    "entero",
    "decimal",
    "cadenita",
    "logico",
    "caracter",
    "vacio",
)


def _texto_tipo(t: Any) -> str:
    """Se obtiene una representacion legible de un tipo."""

    if not isinstance(t, dict):
        return str(t)

    if t.get("tipo") == "personalizado":
        return str(t["nombre"])

    if t.get("tipo") == "lista":
        return f"lista[{_texto_tipo(t['elemento'])}]"

    if t.get("tipo") == "mapa":
        return (
            f"mapa[{_texto_tipo(t['clave'])}, "
            f"{_texto_tipo(t['valor'])}]"
        )

    return str(t)


def tipos_compatibles(
    declarado: Any,
    encontrado: Any
) -> bool:
    """Se comprueba la compatibilidad estructural de los tipos."""

    if (
        declarado == encontrado
        or "cualquiera" in (declarado, encontrado)
    ):
        return True

    if declarado == "decimal" and encontrado == "entero":
        return True

    if encontrado == "nada" and isinstance(declarado, dict):
        return declarado.get("tipo") in (
            "personalizado",
            "lista",
            "mapa",
        )

    if isinstance(declarado, dict) and isinstance(encontrado, dict):

        if declarado.get("tipo") != encontrado.get("tipo"):
            return False

        clase = declarado.get("tipo")

        if clase == "personalizado":
            return (
                declarado.get("nombre")
                == encontrado.get("nombre")
            )

        if clase == "lista":
            return tipos_compatibles(
                declarado["elemento"],
                encontrado["elemento"],
            )

        if clase == "mapa":
            return (
                tipos_compatibles(
                    declarado["clave"],
                    encontrado["clave"],
                )
                and tipos_compatibles(
                    declarado["valor"],
                    encontrado["valor"],
                )
            )

    return False


class AnalizadorJARVIS:
    """Se mantiene el estado del analisis semantico del sistema."""

    def __init__(
        self,
        arbol: dict[str, Any] | None = None,
    ):
        self.arbol = arbol or {}

        self.ambitos: list[dict[str, dict[str, Any]]] = [{}]

        self.acciones: dict[str, dict[str, Any]] = {}
        self.misiones: dict[str, dict[str, Any]] = {}
        self.clases: dict[str, dict[str, Any]] = {}
        self.estructuras: dict[str, dict[str, Any]] = {}
        self.enumeraciones: dict[str, dict[str, Any]] = {}
        self.modulos: dict[str, dict[str, Any]] = {}

        self.accion_actual: dict[str, Any] | None = None
        self.clase_actual: str | None = None
        self.modulo_actual: str | None = None

        self.profundidad_ciclo = 0
        self.profundidad_segun = 0

    @contextmanager
    def ambito(self) -> Iterator[None]:
        """Se crea un ambito local temporal."""

        self.ambitos.append({})

        try:
            yield

        finally:
            self.ambitos.pop()

    def buscar(self, nombre: str) -> dict[str, Any]:
        """Se busca una variable desde el ambito mas cercano."""

        for entorno in reversed(self.ambitos):

            if nombre in entorno:
                return entorno[nombre]

        raise ErrorSemantico(
            f"La variable '{nombre}' no existe"
        )

    def declarar(
        self,
        nombre: str,
        dato: Any,
        clase: str = "var",
    ) -> None:
        """Se registra una variable y se comprueba su tipo."""

        if nombre in self.ambitos[-1]:
            raise ErrorSemantico(
                f"La variable '{nombre}' ya existe en este ambito"
            )

        self.validar_tipo(dato)

        self.ambitos[-1][nombre] = {
            "tipo": dato,
            "clase": clase,
        }

    def validar_tipo(self, dato: Any) -> None:
        """Se comprueba que un tipo este definido en JARVIS."""

        if dato in BASICOS or dato == "cualquiera":
            return

        if isinstance(dato, dict):

            tipo = dato.get("tipo")

            if tipo == "lista":
                self.validar_tipo(dato["elemento"])
                return

            if tipo == "mapa":
                self.validar_tipo(dato["clave"])
                self.validar_tipo(dato["valor"])
                return

            if tipo == "personalizado":

                nombres = (
                    self.clases.keys()
                    | self.estructuras.keys()
                    | self.enumeraciones.keys()
                    | self.modulos.keys()
                )

                if dato.get("nombre") in nombres:
                    return

        raise ErrorSemantico(
            f"Tipo no declarado: {_texto_tipo(dato)}"
        )

    def compatible(
        self,
        esperado: Any,
        real: Any,
    ) -> bool:
        """Se comprueba la compatibilidad, incluida la herencia."""

        if tipos_compatibles(esperado, real):
            return True

        if (
            isinstance(esperado, dict)
            and isinstance(real, dict)
            and esperado.get("tipo") == "personalizado"
            and real.get("tipo") == "personalizado"
        ):
            objetivo = esperado["nombre"]
            actual = real["nombre"]

            visitados = set()

            while (
                actual in self.clases
                and actual not in visitados
            ):

                if objetivo == actual:
                    return True

                visitados.add(actual)

                actual = self.clases[actual].get("hereda")

        return False

    def comun(
        self,
        a: Any,
        b: Any,
        contexto: str,
    ) -> Any:
        """Se determina un tipo comun entre dos valores."""

        if a == "cualquiera":
            return b

        if b == "cualquiera":
            return a

        if self.compatible(a, b):
            return a

        if self.compatible(b, a):
            return b

        raise ErrorSemantico(
            f"{contexto}: tipos incompatibles "
            f"{_texto_tipo(a)} y {_texto_tipo(b)}"
        )

    def registrar(
        self,
        arbol: dict[str, Any],
    ) -> None:
        """Se registran las definiciones disponibles en el sistema."""

        elementos = arbol.get("elementos")

        if elementos is None:
            elementos = (
                arbol.get("globales", [])
                + arbol.get("acciones", [])
                + arbol.get("misiones", [])
                + ([arbol["mision"]] if arbol.get("mision") else [])
                + arbol.get("definiciones", [])
                + arbol.get("vigilancias", [])
            )

        contenedores = {
            "accion": self.acciones,
            "mision": self.misiones,
            "clase": self.clases,
            "estructura": self.estructuras,
            "enumeracion": self.enumeraciones,
            "modulo": self.modulos,
        }

        usados: set[str] = set()

        for elemento in elementos:

            tipo = elemento["tipo"]

            if tipo not in contenedores:
                continue

            nombre = elemento["nombre"]

            if nombre in usados:
                raise ErrorSemantico(
                    f"El nombre '{nombre}' ya fue declarado"
                )

            usados.add(nombre)

            contenedores[tipo][nombre] = elemento

        if "principal" not in self.misiones:
            raise ErrorSemantico(
                "No se encontro la mision principal"
            )

        # Se comprueba que la herencia no forme ciclos.
        for nombre, clase in self.clases.items():

            vistos = {nombre}
            padre = clase.get("hereda")

            while padre:

                if padre not in self.clases:
                    raise ErrorSemantico(
                        f"La clase '{nombre}' hereda de "
                        f"'{padre}', que no existe"
                    )

                if padre in vistos:
                    raise ErrorSemantico(
                        f"Herencia circular detectada en '{nombre}'"
                    )

                vistos.add(padre)

                padre = self.clases[padre].get("hereda")

            miembros = [
                miembro["nombre"]
                for miembro in clase.get("miembros", [])
            ]

            if len(miembros) != len(set(miembros)):
                raise ErrorSemantico(
                    f"La clase '{nombre}' repite miembros"
                )

        # Se comprueban los campos de las estructuras.
        for nombre, estructura in self.estructuras.items():

            campos = estructura.get("campos", [])

            nombres = [
                campo["nombre"]
                for campo in campos
            ]

            if len(nombres) != len(set(nombres)):
                raise ErrorSemantico(
                    f"La estructura '{nombre}' repite campos"
                )

            for campo in campos:
                self.validar_tipo(campo["tipo"])

        # Se comprueba que las enumeraciones no repitan valores.
        for nombre, enumeracion in self.enumeraciones.items():

            valores = enumeracion.get("valores", [])

            if len(valores) != len(set(valores)):
                raise ErrorSemantico(
                    f"La enumeracion '{nombre}' "
                    "contiene valores repetidos"
                )

        # Se registran las referencias a enumeraciones y modulos.
        nombres_globales = (
            self.enumeraciones.keys()
            | self.modulos.keys()
        )

        for nombre in nombres_globales:

            self.ambitos[0][nombre] = {
                "tipo": {
                    "tipo": "personalizado",
                    "nombre": nombre,
                },
                "clase": "fijo",
            }

    def miembro(
        self,
        objeto: Any,
        nombre: str,
    ) -> dict[str, Any]:
        """Se localiza un campo, atributo o metodo."""

        if (
            not isinstance(objeto, dict)
            or objeto.get("tipo") != "personalizado"
        ):
            raise ErrorSemantico(
                f"El tipo {_texto_tipo(objeto)} "
                "no tiene atributos"
            )

        nombre_tipo = objeto["nombre"]

        # Se buscan los campos de una estructura.
        if nombre_tipo in self.estructuras:

            estructura = self.estructuras[nombre_tipo]

            for campo in estructura.get("campos", []):

                if campo["nombre"] == nombre:
                    return {
                        "tipo": "variable",
                        "nombre": nombre,
                        "dato": campo["tipo"],
                        "clase": "var",
                    }

            raise ErrorSemantico(
                f"La estructura '{nombre_tipo}' "
                f"no contiene el campo '{nombre}'"
            )

        # Se consultan los elementos de una enumeracion.
        if nombre_tipo in self.enumeraciones:

            valores = self.enumeraciones[
                nombre_tipo
            ].get("valores", [])

            if nombre in valores:
                return {
                    "tipo": "variable",
                    "nombre": nombre,
                    "dato": objeto,
                    "clase": "fijo",
                }

            raise ErrorSemantico(
                f"La enumeracion '{nombre_tipo}' "
                f"no contiene '{nombre}'"
            )

        # Se consultan las definiciones de un modulo.
        if nombre_tipo in self.modulos:

            elementos = self.modulos[
                nombre_tipo
            ].get("elementos", [])

            for elemento in elementos:

                if elemento.get("nombre") == nombre:
                    return elemento

            raise ErrorSemantico(
                f"El modulo '{nombre_tipo}' "
                f"no contiene '{nombre}'"
            )

        # Se recorren los miembros de una clase y sus padres.
        visitados: set[str] = set()
        actual = nombre_tipo

        while (
            actual in self.clases
            and actual not in visitados
        ):
            visitados.add(actual)

            clase = self.clases[actual]

            for miembro in clase.get("miembros", []):

                if miembro.get("nombre") == nombre:

                    if (
                        miembro.get("visibilidad") == "privado"
                        and self.clase_actual != actual
                    ):
                        raise ErrorSemantico(
                            f"El miembro '{nombre}' es privado"
                        )

                    return miembro

            actual = clase.get("hereda")

        raise ErrorSemantico(
            f"El miembro '{nombre}' no existe"
        )

    def argumentos(
        self,
        nombre: str,
        parametros: list[dict[str, Any]],
        valores: list[Any],
    ) -> None:
        """Se comprueban los argumentos de una accion."""

        if len(parametros) != len(valores):
            raise ErrorSemantico(
                f"La accion '{nombre}' espera "
                f"{len(parametros)} argumento(s), "
                f"pero recibio {len(valores)}"
            )

        for parametro, valor in zip(parametros, valores):

            self.validar_tipo(parametro["tipo"])

            encontrado = self.obtener_tipo(valor)

            if not self.compatible(
                parametro["tipo"],
                encontrado,
            ):
                raise ErrorSemantico(
                    f"La accion '{nombre}' espera "
                    f"{_texto_tipo(parametro['tipo'])} "
                    f"en '{parametro['nombre']}', "
                    f"pero recibio {_texto_tipo(encontrado)}"
                )

    def obtener_tipo(self, e: Any) -> Any:
        """Se determina el tipo de una expresion."""

        if e is None:
            return "nada"

        if type(e) is bool:
            return "logico"

        if type(e) is int:
            return "entero"

        if type(e) is float:
            return "decimal"

        if isinstance(e, str):
            return (
                "logico"
                if e in ("si paso", "no paso")
                else "cadenita"
            )

        if not isinstance(e, dict):
            raise ErrorSemantico(
                "Expresion de tipo desconocido"
            )

        tipo = e.get("tipo")

        # Se consulta el tipo de una variable.
        if tipo == "identificador":
            return self.buscar(e["nombre"])["tipo"]

        if tipo == "cadena":
            return "cadenita"

        if tipo == "caracter":
            return "caracter"

        if tipo == "nada":
            return "nada"

        # Se comprueba el acceso al objeto actual.
        if tipo == "este":

            if self.clase_actual is None:
                raise ErrorSemantico(
                    "'este' solo se admite dentro de una clase"
                )

            return {
                "tipo": "personalizado",
                "nombre": self.clase_actual,
            }

        # Se comprueban los tipos de los elementos de una lista.
        if tipo == "lista":

            dato: Any = "cualquiera"

            for valor in e.get("elementos", []):
                dato = self.comun(
                    dato,
                    self.obtener_tipo(valor),
                    "Lista",
                )

            return {
                "tipo": "lista",
                "elemento": dato,
            }

        # Se comprueban las claves y valores de un mapa.
        if tipo == "mapa":

            clave: Any = "cualquiera"
            valor: Any = "cualquiera"

            for par in e.get("pares", []):

                clave = self.comun(
                    clave,
                    self.obtener_tipo(par["clave"]),
                    "Mapa (claves)",
                )

                valor = self.comun(
                    valor,
                    self.obtener_tipo(par["valor"]),
                    "Mapa (valores)",
                )

            if isinstance(clave, dict):
                raise ErrorSemantico(
                    "Las claves del mapa deben ser tipos basicos"
                )

            return {
                "tipo": "mapa",
                "clave": clave,
                "valor": valor,
            }

        # Se valida el acceso por indice a listas y mapas.
        if tipo == "indice":

            coleccion = self.obtener_tipo(e["objeto"])
            indice = self.obtener_tipo(e["indice"])

            if (
                isinstance(coleccion, dict)
                and coleccion.get("tipo") == "lista"
            ):

                if indice != "entero":
                    raise ErrorSemantico(
                        "El indice de una lista debe ser entero"
                    )

                return coleccion["elemento"]

            if (
                isinstance(coleccion, dict)
                and coleccion.get("tipo") == "mapa"
            ):

                if not self.compatible(
                    coleccion["clave"],
                    indice,
                ):
                    raise ErrorSemantico(
                        "La clave del mapa tiene un tipo incorrecto"
                    )

                return coleccion["valor"]

            raise ErrorSemantico(
                "Solo se pueden indexar listas y mapas"
            )

        # Se resuelve el tipo de un atributo o metodo.
        if tipo == "atributo":

            objeto = self.obtener_tipo(e["objeto"])

            miembro = self.miembro(
                objeto,
                e["nombre"],
            )

            if miembro["tipo"] == "accion":
                return {
                    "tipo": "accion",
                    "firma": miembro,
                }

            return miembro["dato"]

        # Se comprueba la creacion de estructuras y clases.
        if tipo == "crear":

            nombre = e["clase"]
            valores = e.get("argumentos", [])

            # Se valida la creacion de una estructura.
            if nombre in self.estructuras:

                campos = self.estructuras[
                    nombre
                ].get("campos", [])

                if len(campos) != len(valores):
                    raise ErrorSemantico(
                        f"La estructura '{nombre}' requiere "
                        f"{len(campos)} valor(es), "
                        f"pero recibio {len(valores)}"
                    )

                for campo, valor in zip(campos, valores):

                    recibido = self.obtener_tipo(valor)

                    if not self.compatible(
                        campo["tipo"],
                        recibido,
                    ):
                        raise ErrorSemantico(
                            f"El campo '{campo['nombre']}' "
                            f"requiere {_texto_tipo(campo['tipo'])}, "
                            f"pero recibe {_texto_tipo(recibido)}"
                        )

                return {
                    "tipo": "personalizado",
                    "nombre": nombre,
                }

            # Se comprueba la existencia de la clase.
            if nombre not in self.clases:
                raise ErrorSemantico(
                    f"La clase o estructura '{nombre}' no existe"
                )

            iniciador = None
            actual = nombre

            # Se busca el constructor propio o heredado.
            while actual in self.clases:

                iniciador = next(
                    (
                        miembro
                        for miembro in self.clases[
                            actual
                        ].get("miembros", [])
                        if (
                            miembro["tipo"] == "accion"
                            and miembro["nombre"] == "iniciar"
                        )
                    ),
                    None,
                )

                if iniciador:
                    break

                actual = self.clases[actual].get("hereda")

            parametros = (
                iniciador.get("parametros", [])
                if iniciador
                else []
            )

            self.argumentos(
                nombre,
                parametros,
                valores,
            )

            return {
                "tipo": "personalizado",
                "nombre": nombre,
            }

        # Se comprueban llamadas a acciones y funciones.
        if tipo == "llamada":

            valores = e.get("argumentos", [])
            nombre = e.get("nombre")

            # Se validan las funciones integradas.
            if e.get("integrada"):

                if nombre == "preguntar":

                    if len(valores) > 1:
                        raise ErrorSemantico(
                            "preguntar acepta como maximo un argumento"
                        )

                    for valor in valores:
                        self.obtener_tipo(valor)

                    return "cadenita"

                if nombre == "checar":

                    if len(valores) != 1:
                        raise ErrorSemantico(
                            "checar necesita un argumento"
                        )

                    self.obtener_tipo(valores[0])
                    return "logico"

            # Se buscan las acciones globales o del modulo actual.
            if nombre is not None:

                accion = self.acciones.get(nombre)

                if (
                    accion is None
                    and self.modulo_actual is not None
                ):
                    elementos = self.modulos[
                        self.modulo_actual
                    ].get("elementos", [])

                    accion = next(
                        (
                            elemento
                            for elemento in elementos
                            if (
                                elemento.get("tipo") == "accion"
                                and elemento.get("nombre") == nombre
                            )
                        ),
                        None,
                    )

                if accion is None:
                    raise ErrorSemantico(
                        f"La accion '{nombre}' no existe"
                    )

            else:
                destino = self.obtener_tipo(
                    e["objetivo"]
                )

                if (
                    not isinstance(destino, dict)
                    or destino.get("tipo") != "accion"
                ):
                    raise ErrorSemantico(
                        "El destino no es una accion"
                    )

                accion = destino["firma"]
                nombre = accion["nombre"]

            self.argumentos(
                nombre,
                accion.get("parametros", []),
                valores,
            )

            return accion.get("retorno") or "vacio"

        # Se comprueban los operadores unarios.
        if tipo == "unario":

            valor = self.obtener_tipo(e["valor"])

            if e["operador"] == "negar":

                if valor != "logico":
                    raise ErrorSemantico(
                        "negar requiere un valor logico"
                    )

                return "logico"

            if valor not in NUMERICOS:
                raise ErrorSemantico(
                    "El signo requiere un numero"
                )

            return valor

        # Se comprueban operaciones y comparaciones.
        if tipo in ("operacion", "comparacion", "logica"):

            izquierda = self.obtener_tipo(e["izquierda"])
            derecha = self.obtener_tipo(e["derecha"])

            operador = e["operador"]

            if tipo == "logica":

                if (
                    izquierda != "logico"
                    or derecha != "logico"
                ):
                    raise ErrorSemantico(
                        "Los operadores logicos "
                        "necesitan valores logicos"
                    )

                return "logico"

            if tipo == "comparacion":

                if operador in ("==", "!="):

                    if not (
                        self.compatible(izquierda, derecha)
                        or self.compatible(derecha, izquierda)
                    ):
                        raise ErrorSemantico(
                            "Comparacion entre tipos incompatibles"
                        )

                elif (
                    izquierda not in NUMERICOS
                    or derecha not in NUMERICOS
                ):
                    raise ErrorSemantico(
                        "Las comparaciones de orden requieren numeros"
                    )

                return "logico"

            # Se permite concatenar dos cadenas.
            if (
                operador == "+"
                and izquierda == "cadenita"
                and derecha == "cadenita"
            ):
                return "cadenita"

            if (
                izquierda not in NUMERICOS
                or derecha not in NUMERICOS
            ):
                raise ErrorSemantico(
                    f"Operacion '{operador}' invalida entre "
                    f"{_texto_tipo(izquierda)} y "
                    f"{_texto_tipo(derecha)}"
                )

            if operador == "/":
                return "decimal"

            if operador == "div":
                return "entero"

            return (
                "decimal"
                if "decimal" in (izquierda, derecha)
                else "entero"
            )

        raise ErrorSemantico(
            f"Expresion no implementada: {tipo}"
        )

    def lvalor(
        self,
        objetivo: dict[str, Any],
    ) -> tuple[Any, dict[str, Any] | None]:
        """Se comprueba si un destino puede recibir una asignacion."""

        raiz = objetivo

        while raiz.get("tipo") in ("indice", "atributo"):
            raiz = raiz["objeto"]

        # Se impide modificar una constante.
        if raiz.get("tipo") == "identificador":

            simbolo = self.buscar(raiz["nombre"])

            if simbolo.get("clase") == "fijo":
                raise ErrorSemantico(
                    f"No se puede modificar la constante "
                    f"'{raiz['nombre']}'"
                )

        # Se comprueba que el atributo sea modificable.
        if objetivo.get("tipo") == "atributo":

            miembro = self.miembro(
                self.obtener_tipo(objetivo["objeto"]),
                objetivo["nombre"],
            )

            if miembro.get("tipo") == "accion":
                raise ErrorSemantico(
                    "No se puede asignar a un metodo"
                )

            if miembro.get("clase") == "fijo":
                raise ErrorSemantico(
                    f"No se puede modificar la constante "
                    f"'{objetivo['nombre']}'"
                )

        return self.obtener_tipo(objetivo), None

    def analizar_instruccion(
        self,
        i: dict[str, Any],
    ) -> None:
        """Se comprueba una instruccion del AST."""

        tipo = i["tipo"]

        # Se comprueba una declaracion de variable.
        if tipo == "variable":

            nombre = i["nombre"]
            dato = i.get("dato")
            valor = i.get("valor")
            clase = i.get("clase", "var")

            if clase == "fijo" and valor is None:
                raise ErrorSemantico(
                    f"La constante '{nombre}' "
                    "requiere un valor inicial"
                )

            if dato is None and valor is None:
                raise ErrorSemantico(
                    f"La variable '{nombre}' "
                    "necesita tipo o valor"
                )

            real = (
                self.obtener_tipo(valor)
                if valor is not None
                else None
            )

            if dato is None:
                dato = real

            elif (
                real is not None
                and not self.compatible(dato, real)
            ):
                raise ErrorSemantico(
                    f"La variable '{nombre}' es de tipo "
                    f"{_texto_tipo(dato)}, "
                    f"pero recibe {_texto_tipo(real)}"
                )

            if dato in ("vacio", "nada"):
                raise ErrorSemantico(
                    f"La variable '{nombre}' "
                    "no puede ser de tipo vacio"
                )

            self.declarar(
                nombre,
                dato,
                clase,
            )

            return

        # Se comprueba una asignacion.
        if tipo == "asignacion":

            objetivo = i.get("objetivo") or {
                "tipo": "identificador",
                "nombre": i["nombre"],
            }

            esperado, _ = self.lvalor(objetivo)

            real = self.obtener_tipo(i["valor"])
            operador = i.get("operador", "=")

            if operador == "=":

                if not self.compatible(esperado, real):
                    raise ErrorSemantico(
                        f"No se puede asignar "
                        f"{_texto_tipo(real)} "
                        f"a {_texto_tipo(esperado)}"
                    )

            else:

                # La concatenacion += tambien admite cadenas de texto.
                if (
                    operador == "+="
                    and esperado == "cadenita"
                    and real == "cadenita"
                ):
                    return

                operadores_compuestos = {
                    "+=", "-=", "*=", "/=", "%=", "**="
                }

                if operador not in operadores_compuestos:
                    raise ErrorSemantico(
                        f"Operador de asignacion desconocido: '{operador}'"
                    )

                if (
                    esperado not in NUMERICOS
                    or real not in NUMERICOS
                ):
                    raise ErrorSemantico(
                        f"El operador '{operador}' requiere numeros"
                    )

                if (
                    esperado == "entero"
                    and (
                        real == "decimal"
                        or operador == "/="
                    )
                ):
                    raise ErrorSemantico(
                        "No se puede almacenar una operacion "
                        "decimal en entero"
                    )

            return

        # Se comprueban instrucciones de salida.
        if tipo in ("imprimir", "alerta", "registrar"):

            argumentos = i.get(
                "argumentos",
                [i.get("mensaje")],
            )

            for valor in argumentos:
                self.obtener_tipo(valor)

            return

        # Se comprueban las condiciones.
        if tipo == "si":

            if self.obtener_tipo(i["condicion"]) != "logico":
                raise ErrorSemantico(
                    "La condicion SI debe ser logica"
                )

            self.bloque(i["instrucciones_si"])
            self.bloque(i["instrucciones_sino"])

            return

        # Se comprueban los casos de una seleccion.
        if tipo == "segun":

            dato = self.obtener_tipo(i["valor"])

            self.profundidad_segun += 1

            try:
                for caso in i["casos"]:

                    real = self.obtener_tipo(caso["valor"])

                    if not (
                        self.compatible(dato, real)
                        or self.compatible(real, dato)
                    ):
                        raise ErrorSemantico(
                            "Caso de tipo incompatible"
                        )

                    self.bloque(caso["instrucciones"])

                self.bloque(i.get("otro_caso", []))

            finally:
                self.profundidad_segun -= 1

            return

        # Se comprueban los ciclos repetir y mientras.
        if tipo in ("repetir", "mientras"):

            clave = (
                "cantidad"
                if tipo == "repetir"
                else "condicion"
            )

            condicion = self.obtener_tipo(i[clave])

            esperado = (
                "entero"
                if tipo == "repetir"
                else "logico"
            )

            if condicion != esperado:
                raise ErrorSemantico(
                    f"{tipo.upper()} requiere un tipo correcto"
                )

            self.profundidad_ciclo += 1

            try:
                self.bloque(i["instrucciones"])

            finally:
                self.profundidad_ciclo -= 1

            return

        # Se comprueban ciclos para y para_en.
        if tipo in ("para", "para_en"):

            with self.ambito():

                if tipo == "para":

                    if i.get("inicio"):
                        self.analizar_instruccion(i["inicio"])

                    if self.obtener_tipo(i["condicion"]) != "logico":
                        raise ErrorSemantico(
                            "La condicion PARA debe ser logica"
                        )

                    if i.get("cambio"):
                        self.analizar_instruccion(i["cambio"])

                else:
                    coleccion = self.obtener_tipo(
                        i["coleccion"]
                    )

                    if (
                        not isinstance(coleccion, dict)
                        or coleccion.get("tipo")
                        not in ("lista", "mapa")
                    ):
                        raise ErrorSemantico(
                            "PARA EN requiere una lista o mapa"
                        )

                    elemento = (
                        coleccion["elemento"]
                        if coleccion["tipo"] == "lista"
                        else coleccion["clave"]
                    )

                    iterador = i["iterador"]

                    if iterador["declarar"]:
                        self.declarar(
                            iterador["nombre"],
                            elemento,
                        )

                    elif not self.compatible(
                        self.buscar(iterador["nombre"])["tipo"],
                        elemento,
                    ):
                        raise ErrorSemantico(
                            "Iterador de tipo incompatible"
                        )

                self.profundidad_ciclo += 1

                try:
                    self.bloque(i["instrucciones"])

                finally:
                    self.profundidad_ciclo -= 1

            return

        # Se comprueba detener y seguir.
        if tipo in ("detener", "seguir"):

            permitido = (
                self.profundidad_ciclo
                or (
                    tipo == "detener"
                    and self.profundidad_segun
                )
            )

            if not permitido:
                raise ErrorSemantico(
                    f"'{tipo}' fuera de su contexto permitido"
                )

            return

        # Se comprueba el valor devuelto por una accion.
        if tipo == "devolver":

            if self.accion_actual is None:
                raise ErrorSemantico(
                    "devolver solo puede usarse en una accion"
                )

            esperado = (
                self.accion_actual.get("retorno")
                or "vacio"
            )

            real = (
                self.obtener_tipo(i["valor"])
                if i.get("valor") is not None
                else "vacio"
            )

            if not self.compatible(esperado, real):
                raise ErrorSemantico(
                    f"Retorno incorrecto: se esperaba "
                    f"{_texto_tipo(esperado)}, "
                    f"se recibio {_texto_tipo(real)}"
                )

            return

        # Se comprueba la ejecucion de misiones secundarias.
        if tipo == "ejecutar":

            if i["nombre"] not in self.misiones:
                raise ErrorSemantico(
                    f"La mision '{i['nombre']}' no existe"
                )

            return

        # Se comprueba el manejo de errores.
        if tipo == "proteger":

            if (
                not i.get("atrapar")
                and not i.get("finalmente")
            ):
                raise ErrorSemantico(
                    "proteger requiere atrapar o finalmente"
                )

            self.bloque(i["instrucciones"])

            capturador = i.get("atrapar")

            if capturador:

                with self.ambito():

                    self.declarar(
                        capturador["nombre"],
                        "cadenita",
                    )

                    self.bloque(
                        capturador["instrucciones"],
                        nuevo=False,
                    )

            self.bloque(i.get("finalmente", []))

            return

        # Se comprueba la instruccion lanzar.
        if tipo == "lanzar":
            self.obtener_tipo(i["valor"])
            return

        # Se comprueba la condicion de vigilancia.
        if tipo == "vigilar":

            if self.obtener_tipo(i["condicion"]) != "logico":
                raise ErrorSemantico(
                    "La condicion VIGILAR debe ser logica"
                )

            self.bloque(i["instrucciones"])

            return

        # Se comprueban las expresiones independientes.
        expresiones = (
            "llamada",
            "crear",
            "identificador",
            "operacion",
            "comparacion",
            "logica",
            "unario",
            "lista",
            "mapa",
            "indice",
            "atributo",
            "cadena",
            "caracter",
            "nada",
        )

        if tipo in expresiones:
            self.obtener_tipo(i)
            return

        raise ErrorSemantico(
            f"Instruccion no implementada: {tipo}"
        )

    def bloque(
        self,
        instrucciones: list[dict[str, Any]],
        nuevo: bool = True,
    ) -> None:
        """Se analizan las instrucciones dentro de su ambito."""

        if nuevo:

            with self.ambito():

                for instruccion in instrucciones:
                    self.analizar_instruccion(instruccion)

        else:

            for instruccion in instrucciones:
                self.analizar_instruccion(instruccion)

    def analizar_accion(
        self,
        a: dict[str, Any],
        clase: str | None = None,
        modulo: str | None = None,
    ) -> None:
        """Se valida una accion y sus parametros."""

        accion_anterior = self.accion_actual
        clase_anterior = self.clase_actual
        modulo_anterior = self.modulo_actual

        self.accion_actual = a
        self.clase_actual = clase
        self.modulo_actual = modulo

        try:
            with self.ambito():

                for parametro in a.get("parametros", []):

                    self.declarar(
                        parametro["nombre"],
                        parametro["tipo"],
                        "parametro",
                    )

                if a.get("retorno") is not None:
                    self.validar_tipo(a["retorno"])

                self.bloque(
                    a["instrucciones"],
                    nuevo=False,
                )

                retorno = a.get("retorno")

                if (
                    retorno not in (None, "vacio")
                    and not self._retorna(a["instrucciones"])
                ):
                    raise ErrorSemantico(
                        f"La accion '{a['nombre']}' "
                        "debe devolver un valor"
                    )

        finally:
            self.accion_actual = accion_anterior
            self.clase_actual = clase_anterior
            self.modulo_actual = modulo_anterior

    def _retorna(
        self,
        instrucciones: list[dict[str, Any]],
    ) -> bool:
        """Se comprueba si una accion contiene un retorno obligatorio."""

        for instruccion in instrucciones:

            if instruccion["tipo"] == "devolver":
                return True

            if (
                instruccion["tipo"] == "si"
                and instruccion.get("instrucciones_sino")
            ):

                if (
                    self._retorna(
                        instruccion["instrucciones_si"]
                    )
                    and self._retorna(
                        instruccion["instrucciones_sino"]
                    )
                ):
                    return True

        return False

    def analizar(
        self,
        arbol: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        """Se realiza el analisis semantico de todo el sistema."""

        self.registrar(arbol)

        # Se registran y comprueban las variables globales.
        for variable in arbol.get("globales", []):
            self.analizar_instruccion(variable)

        # Se comprueban las acciones globales.
        for accion in self.acciones.values():
            self.analizar_accion(accion)

        # Se comprueban los miembros de las clases.
        for clase in self.clases.values():

            for miembro in clase.get("miembros", []):

                if miembro["tipo"] == "accion":

                    self.analizar_accion(
                        miembro,
                        clase=clase["nombre"],
                    )

                elif miembro["tipo"] == "variable":

                    anterior = self.clase_actual
                    self.clase_actual = clase["nombre"]

                    try:
                        with self.ambito():
                            self.analizar_instruccion(miembro)

                    finally:
                        self.clase_actual = anterior

        # Se comprueban las declaraciones de los modulos.
        for modulo in self.modulos.values():

            with self.ambito():

                for elemento in modulo.get("elementos", []):

                    if elemento["tipo"] == "variable":
                        self.analizar_instruccion(elemento)

                for elemento in modulo.get("elementos", []):

                    if elemento["tipo"] == "accion":

                        self.analizar_accion(
                            elemento,
                            modulo=modulo["nombre"],
                        )

        # Se comprueba que los modulos importados existan.
        for definicion in arbol.get("definiciones", []):

            if definicion["tipo"] == "usar":

                nombre = definicion["ruta"].split(".")[0]

                if nombre not in self.modulos:
                    raise ErrorSemantico(
                        f"El modulo '{definicion['ruta']}' no existe"
                    )

        # Se comprueban las vigilancias globales.
        for vigilancia in arbol.get("vigilancias", []):
            self.analizar_instruccion(vigilancia)

        # Se comprueban las misiones.
        variables_mision: dict[str, dict[str, Any]] = {}

        for mision in self.misiones.values():

            with self.ambito():

                self.bloque(
                    mision["instrucciones"],
                    nuevo=False,
                )

                if mision["nombre"] == "principal":
                    variables_mision = dict(
                        self.ambitos[-1]
                    )

        # Se actualiza la tabla utilizada por la interfaz.
        tabla_simbolos.clear()

        tabla_simbolos.update(
            self.ambitos[0]
        )

        tabla_simbolos.update(
            variables_mision
        )

        # Se conserva el registro de acciones.
        tabla_acciones.clear()

        tabla_acciones.update(
            self.acciones
        )

        return tabla_simbolos


_analizador_actual: AnalizadorJARVIS | None = None


def obtener_tipo(valor: Any) -> Any:
    """Se conserva la funcion publica de consulta de tipos."""

    analizador = (
        _analizador_actual
        or AnalizadorJARVIS()
    )

    if _analizador_actual is None:

        analizador.ambitos[0].update(
            tabla_simbolos
        )

        analizador.acciones.update(
            tabla_acciones
        )

    return analizador.obtener_tipo(valor)


def analizar_instruccion(
    instruccion: dict[str, Any],
) -> None:
    """Se conserva la funcion publica de validacion."""

    analizador = (
        _analizador_actual
        or AnalizadorJARVIS()
    )

    if _analizador_actual is None:

        analizador.ambitos[0].update(
            tabla_simbolos
        )

        analizador.acciones.update(
            tabla_acciones
        )

    analizador.analizar_instruccion(
        instruccion
    )

    if _analizador_actual is None:

        tabla_simbolos.update(
            analizador.ambitos[0]
        )


def registrar_acciones(
    arbol: dict[str, Any],
) -> None:
    """Se registran las acciones del programa."""

    tabla_acciones.clear()

    for accion in arbol.get("acciones", []):

        nombre = accion["nombre"]

        if nombre in tabla_acciones:
            raise ErrorSemantico(
                f"La accion '{nombre}' ya existe"
            )

        tabla_acciones[nombre] = accion


def analizar_programa(
    arbol: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Se analiza un AST completo de JARVIS."""

    global _analizador_actual

    if (
        not isinstance(arbol, dict)
        or arbol.get("tipo") != "sistema"
    ):
        raise ErrorSemantico(
            "El programa no contiene "
            "un sistema JARVIS valido"
        )

    tabla_simbolos.clear()
    tabla_acciones.clear()

    anterior = _analizador_actual

    analizador = AnalizadorJARVIS(arbol)

    _analizador_actual = analizador

    try:
        return analizador.analizar(arbol)

    finally:
        _analizador_actual = anterior


def mostrar_resultados(
    resultado: dict[str, dict[str, Any]],
) -> None:
    """Se muestran los resultados del analisis."""

    print("========== JARVIS ==========")
    print("Analisis semantico correcto")

    for nombre, dato in resultado.items():

        print(
            f"Variable: {nombre} | "
            f"Tipo: {_texto_tipo(dato['tipo'])}"
        )

    print("Sin errores semanticos detectados")


if __name__ == "__main__":
    from alexico import lexer
    from asintactico import parser, codigo

    lexer.lineno = 1

    try:
        arbol = parser.parse(
            codigo,
            lexer=lexer,
        )

        resultado = analizar_programa(arbol)

        mostrar_resultados(resultado)

    except (SyntaxError, ErrorSemantico) as error:

        print("========== ERROR JARVIS ==========")
        print(error)

