"""Se interpreta el AST construido por asintactico.py despues de su
validacion semantica. Se conserva la API utilizada por cijarvis.py.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable, Iterator
from contextlib import contextmanager
from typing import Any
import sys

from alexico import lexer
from asintactico import parser, codigo
from asemantico import analizar_programa, ErrorSemantico, tipos_compatibles


class ErrorEjecucionJARVIS(ValueError):
    """Se informa un fallo de ejecucion controlado."""


class _Devolver(Exception):
    def __init__(self, valor: Any) -> None:
        self.valor = valor


class _Detener(Exception):
    pass


class _Seguir(Exception):
    pass


class InstanciaJARVIS:
    def __init__(self, nombre_clase: str) -> None:
        self.nombre_clase = nombre_clase
        self.atributos: dict[str, Any] = {}
        self.metadatos: dict[str, dict[str, Any]] = {}

    def __repr__(self) -> str:
        return f"<objeto {self.nombre_clase}>"


class ModuloJARVIS:
    def __init__(self, nombre: str) -> None:
        self.nombre = nombre
        self.variables: dict[str, Any] = {}
        self.metadatos: dict[str, dict[str, Any]] = {}
        self.acciones: dict[str, dict[str, Any]] = {}

    def __repr__(self) -> str:
        return f"<modulo {self.nombre}>"


class EnumeracionJARVIS:
    def __init__(self, enumeracion: str, nombre: str) -> None:
        self.enumeracion = enumeracion
        self.nombre = nombre

    def __eq__(self, otro: object) -> bool:
        return (
            isinstance(otro, EnumeracionJARVIS)
            and self.enumeracion == otro.enumeracion
            and self.nombre == otro.nombre
        )

    def __hash__(self) -> int:
        return hash((self.enumeracion, self.nombre))

    def __repr__(self) -> str:
        return f"{self.enumeracion}.{self.nombre}"


class AccionEnlazada:
    def __init__(
        self,
        accion: dict[str, Any],
        objeto: InstanciaJARVIS | None = None,
        modulo: ModuloJARVIS | None = None,
        clase: str | None = None,
    ) -> None:
        self.accion = accion
        self.objeto = objeto
        self.modulo = modulo
        self.clase = clase


class EjecutorJARVIS:
    MAX_ITERACIONES = 10000
    MAX_LLAMADAS = 100

    def __init__(
        self,
        proveedor_entrada: Callable[[str], str] | None = None,
    ) -> None:
        # Se conserva la interfaz publica del ejecutor.
        self.variables: dict[str, Any] = {}
        self.acciones: dict[str, dict[str, Any]] = {}
        self.pila_acciones: list[str] = []

        self._ambitos: list[dict[str, Any]] = [self.variables]
        self._metadatos: list[dict[str, dict[str, Any]]] = [{}]

        self._objeto_actual: InstanciaJARVIS | None = None
        self._clase_actual: str | None = None

        self.vigilancias: list[dict[str, Any]] = []
        self._vigilando = False
        self._contador_misiones = 0

        self.misiones: dict[str, dict[str, Any]] = {}
        self.clases: dict[str, dict[str, Any]] = {}
        self.estructuras: dict[str, dict[str, Any]] = {}
        self.enumeraciones: dict[str, dict[str, Any]] = {}
        self.modulos: dict[str, ModuloJARVIS] = {}

        self.proveedor_entrada = proveedor_entrada

    @contextmanager
    def _ambito(self) -> Iterator[None]:
        # Se aislan variables locales y vigilancias del bloque.
        inicio = len(self.vigilancias)

        self._ambitos.append({})
        self._metadatos.append({})

        try:
            yield
        finally:
            del self.vigilancias[inicio:]
            self._ambitos.pop()
            self._metadatos.pop()

    def _buscar(
        self,
        nombre: str
    ) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
        # Se busca el identificador desde el ambito mas cercano.
        for posicion in range(len(self._ambitos) - 1, -1, -1):
            if nombre in self._ambitos[posicion]:
                return (
                    self._ambitos[posicion],
                    self._metadatos[posicion]
                )

        raise ErrorEjecucionJARVIS(
            f"La variable '{nombre}' no existe"
        )

    def _tipo_valor(self, valor: Any) -> Any:
        # Se identifica el tipo real del valor recibido.
        if valor is None:
            return "nada"

        if type(valor) is bool:
            return "logico"

        if type(valor) is int:
            return "entero"

        if type(valor) is float:
            return "decimal"

        if type(valor) is str:
            return "cadenita"

        if isinstance(valor, InstanciaJARVIS):
            return {
                "tipo": "personalizado",
                "nombre": valor.nombre_clase
            }

        if isinstance(valor, EnumeracionJARVIS):
            return {
                "tipo": "personalizado",
                "nombre": valor.enumeracion
            }

        if isinstance(valor, ModuloJARVIS):
            return {
                "tipo": "personalizado",
                "nombre": valor.nombre
            }

        if isinstance(valor, list):
            return {
                "tipo": "lista",
                "elemento": "cualquiera"
            }

        if isinstance(valor, dict):
            return {
                "tipo": "mapa",
                "clave": "cualquiera",
                "valor": "cualquiera"
            }

        return type(valor).__name__

    def _normalizar(
        self,
        esperado: Any,
        valor: Any,
        nombre: str
    ) -> Any:
        # Se valida cada asignacion antes de guardar su valor.
        if esperado is None or esperado == "cualquiera":
            return valor

        if esperado == "decimal" and type(valor) is int:
            return float(valor)

        if (
            esperado == "caracter"
            and type(valor) is str
            and len(valor) == 1
        ):
            return valor

        if isinstance(esperado, dict):
            clase = esperado.get("tipo")

            if (
                valor is None
                and clase in ("personalizado", "lista", "mapa")
            ):
                return valor

            if clase == "lista" and isinstance(valor, list):
                for elemento in valor:
                    self._normalizar(
                        esperado["elemento"],
                        elemento,
                        nombre
                    )
                return valor

            if clase == "mapa" and isinstance(valor, dict):
                for clave, elemento in valor.items():
                    self._normalizar(
                        esperado["clave"],
                        clave,
                        nombre
                    )
                    self._normalizar(
                        esperado["valor"],
                        elemento,
                        nombre
                    )
                return valor

        # Se admite una instancia de una clase hija donde se espera
        # su clase padre, como permite el analizador semantico.
        if (
            isinstance(esperado, dict)
            and esperado.get("tipo") == "personalizado"
            and isinstance(valor, InstanciaJARVIS)
            and valor.nombre_clase in self.clases
            and esperado.get("nombre") in {
                clase["nombre"]
                for clase in self._jerarquia(
                    valor.nombre_clase, inversa=True
                )
            }
        ):
            return valor

        if not tipos_compatibles(
            esperado,
            self._tipo_valor(valor)
        ):
            raise ErrorEjecucionJARVIS(
                f"El valor de '{nombre}' "
                f"no corresponde al tipo {esperado}"
            )

        return valor

    def _declarar(
        self,
        nombre: str,
        valor: Any,
        tipo: Any = None,
        clase: str = "var"
    ) -> None:
        # Se registra una variable en el ambito actual.
        if nombre in self._ambitos[-1]:
            raise ErrorEjecucionJARVIS(
                f"La variable '{nombre}' ya existe"
            )

        if tipo is None:
            tipo = self._tipo_valor(valor)

        if valor is not None:
            valor = self._normalizar(
                tipo,
                valor,
                nombre
            )

        self._ambitos[-1][nombre] = valor
        self._metadatos[-1][nombre] = {
            "tipo": tipo,
            "clase": clase
        }

        self._comprobar_vigilancias()

    def _asignar_nombre(
        self,
        nombre: str,
        valor: Any
    ) -> None:
        # Se modifica una variable existente.
        ambito, meta = self._buscar(nombre)
        datos = meta.get(nombre, {})

        if datos.get("clase") == "fijo":
            raise ErrorEjecucionJARVIS(
                f"No se puede modificar "
                f"la constante '{nombre}'"
            )

        ambito[nombre] = self._normalizar(
            datos.get("tipo"),
            valor,
            nombre
        )

        self._comprobar_vigilancias()

    def evaluar(self, expresion: Any) -> Any:
        """Se interpreta una expresion y se devuelve su valor."""

        # Se distinguen los valores simples de los nodos AST.
        if not isinstance(expresion, dict):
            if expresion == "si paso":
                return True

            if expresion == "no paso":
                return False

            return expresion

        tipo = expresion.get("tipo")

        # Se consultan identificadores y acciones.
        if tipo == "identificador":
            nombre = expresion["nombre"]

            try:
                ambito, _ = self._buscar(nombre)
                return ambito[nombre]

            except ErrorEjecucionJARVIS:
                if nombre in self.acciones:
                    return AccionEnlazada(
                        self.acciones[nombre]
                    )
                raise

        # Se recuperan los valores literales.
        if tipo in ("cadena", "caracter", "nada"):
            return expresion["valor"]

        # Se recupera el objeto actual.
        if tipo == "este":
            if self._objeto_actual is None:
                raise ErrorEjecucionJARVIS(
                    "'este' requiere una instancia"
                )

            return self._objeto_actual

        # Se construye una lista.
        if tipo == "lista":
            return [
                self.evaluar(elemento)
                for elemento in expresion["elementos"]
            ]

        # Se construye un mapa utilizando claves validas.
        if tipo == "mapa":
            resultado: dict[Hashable, Any] = {}

            for par in expresion["pares"]:
                clave: Any = self.evaluar(par["clave"])
                valor: Any = self.evaluar(par["valor"])

                if not isinstance(clave, Hashable):
                    raise ErrorEjecucionJARVIS(
                        "Un mapa requiere claves hashables"
                    )

                try:
                    hash(clave)
                    resultado[clave] = valor

                except TypeError as error:
                    raise ErrorEjecucionJARVIS(
                        "La clave del mapa no es valida"
                    ) from error

            return resultado

        # Se obtiene un elemento por indice.
        if tipo == "indice":
            objeto: Any = self.evaluar(
                expresion["objeto"]
            )

            indice: Any = self.evaluar(
                expresion["indice"]
            )

            if not isinstance(objeto, (list, dict)):
                raise ErrorEjecucionJARVIS(
                    "Solo se pueden indexar listas y mapas"
                )

            try:
                return objeto[indice]

            except (
                IndexError,
                KeyError,
                TypeError
            ) as error:
                raise ErrorEjecucionJARVIS(
                    f"Indice o clave inexistente: {indice}"
                ) from error

        # Se consulta un atributo.
        if tipo == "atributo":
            return self._atributo(
                self.evaluar(expresion["objeto"]),
                expresion["nombre"]
            )

        # Se crea un objeto.
        if tipo == "crear":
            valores = [
                self.evaluar(argumento)
                for argumento in expresion["argumentos"]
            ]

            return self._crear_objeto(
                expresion["clase"],
                valores
            )

        # Se ejecuta una llamada.
        if tipo == "llamada":
            valores = [
                self.evaluar(argumento)
                for argumento in expresion.get("argumentos", [])
            ]

            nombre = expresion.get("nombre")

            if expresion.get("integrada"):
                return self._integrada(
                    nombre,
                    valores
                )

            if nombre is not None:
                return self.ejecutar_accion(
                    nombre,
                    valores,
                    evaluados=True
                )

            destino = self.evaluar(
                expresion["objetivo"]
            )

            if not isinstance(destino, AccionEnlazada):
                raise ErrorEjecucionJARVIS(
                    "El destino no es una accion"
                )

            return self._llamar(destino, valores)

        # Se interpretan operadores unarios.
        if tipo == "unario":
            valor = self.evaluar(
                expresion["valor"]
            )

            operador = expresion["operador"]

            if operador == "negar":
                if type(valor) is not bool:
                    raise TypeError(
                        "negar requiere un valor logico"
                    )
                return not valor

            if type(valor) not in (int, float):
                raise TypeError(
                    "El signo requiere un numero"
                )

            return -valor if operador == "-" else +valor

        # Se interpretan operadores logicos.
        if tipo == "logica":
            izquierda = self.evaluar(
                expresion["izquierda"]
            )

            if type(izquierda) is not bool:
                raise TypeError(
                    "y/o requieren valores logicos"
                )

            operador = expresion["operador"]

            # Se aplica evaluacion de cortocircuito.
            if operador == "y" and not izquierda:
                return False

            if operador == "o" and izquierda:
                return True

            derecha = self.evaluar(
                expresion["derecha"]
            )

            if type(derecha) is not bool:
                raise TypeError(
                    "y/o requieren valores logicos"
                )

            if operador == "y":
                return izquierda and derecha

            return izquierda or derecha

        # Se interpretan operaciones y comparaciones.
        if tipo in ("operacion", "comparacion"):
            izquierda: Any = self.evaluar(
                expresion["izquierda"]
            )

            derecha: Any = self.evaluar(
                expresion["derecha"]
            )

            operador = expresion["operador"]

            if operador == "==":
                return izquierda == derecha

            if operador == "!=":
                return izquierda != derecha

            # Se realizan comparaciones numericas.
            if operador in (">", "<", ">=", "<="):
                if (
                    type(izquierda) not in (int, float)
                    or type(derecha) not in (int, float)
                ):
                    raise TypeError(
                        "La comparacion requiere numeros"
                    )

                if operador == ">":
                    return izquierda > derecha

                if operador == "<":
                    return izquierda < derecha

                if operador == ">=":
                    return izquierda >= derecha

                return izquierda <= derecha

            # Se realizan operaciones matematicas.
            if operador == "+":
                return izquierda + derecha

            if operador == "-":
                return izquierda - derecha

            if operador == "*":
                return izquierda * derecha

            if operador == "/":
                return izquierda / derecha

            if operador == "div":
                return int(izquierda / derecha)

            if operador == "%":
                return izquierda % derecha

            if operador == "**":
                if abs(derecha) > 10000:
                    raise ErrorEjecucionJARVIS(
                        "El exponente es demasiado grande"
                    )

                return izquierda ** derecha

            raise ErrorEjecucionJARVIS(
                f"Operador desconocido: {operador}"
            )

        raise ErrorEjecucionJARVIS(
            f"Expresion no implementada: {tipo}"
        )

    def convertir_salida(self, valor: Any) -> str:
        # Se muestran los valores con la notacion de JARVIS.
        if valor is True:
            return "si paso"

        if valor is False:
            return "no paso"

        if valor is None:
            return "nada"

        if isinstance(valor, list):
            elementos = ", ".join(
                self.convertir_salida(elemento)
                for elemento in valor
            )
            return f"[{elementos}]"

        if isinstance(valor, dict):
            elementos = ", ".join(
                f"{self.convertir_salida(clave)}: "
                f"{self.convertir_salida(elemento)}"
                for clave, elemento in valor.items()
            )
            return "{" + elementos + "}"

        return str(valor)

    def registrar_acciones(
        self,
        arbol: dict[str, Any]
    ) -> None:
        # Se registran las acciones del sistema.
        self.acciones.clear()

        for accion in arbol.get("acciones", []):
            nombre = accion["nombre"]

            if nombre in self.acciones:
                raise ErrorEjecucionJARVIS(
                    f"Accion duplicada: {nombre}"
                )

            self.acciones[nombre] = accion

    def _jerarquia(
        self,
        nombre: str,
        inversa: bool = False
    ) -> list[dict[str, Any]]:
        # Se recorre la herencia de una clase.
        resultado: list[dict[str, Any]] = []
        visitados: set[str] = set()
        actual: str | None = nombre

        while actual:
            if actual in visitados:
                raise ErrorEjecucionJARVIS(
                    "Herencia circular detectada"
                )

            visitados.add(actual)

            definicion = self.clases.get(actual)

            if definicion is None:
                raise ErrorEjecucionJARVIS(
                    f"La clase '{actual}' no existe"
                )

            resultado.append(definicion)
            actual = definicion.get("hereda")

        return resultado if inversa else list(reversed(resultado))

    def _atributo(
        self,
        objeto: Any,
        nombre: str
    ) -> Any:
        # Se consultan atributos y metodos de instancias.
        if isinstance(objeto, InstanciaJARVIS):
            if nombre in objeto.atributos:
                meta = objeto.metadatos.get(nombre, {})

                if (
                    meta.get("visibilidad") == "privado"
                    and self._clase_actual != meta.get("origen")
                ):
                    raise ErrorEjecucionJARVIS(
                        f"El atributo '{nombre}' es privado"
                    )

                return objeto.atributos[nombre]

            for clase in self._jerarquia(
                objeto.nombre_clase,
                inversa=True
            ):
                for miembro in clase["miembros"]:
                    if (
                        miembro["tipo"] == "accion"
                        and miembro["nombre"] == nombre
                    ):
                        if (
                            miembro.get("visibilidad") == "privado"
                            and self._clase_actual != clase["nombre"]
                        ):
                            raise ErrorEjecucionJARVIS(
                                f"La accion '{nombre}' es privada"
                            )

                        return AccionEnlazada(
                            miembro,
                            objeto=objeto,
                            clase=clase["nombre"]
                        )

            raise ErrorEjecucionJARVIS(
                f"El miembro '{nombre}' no existe"
            )

        # Se consultan elementos de modulos.
        if isinstance(objeto, ModuloJARVIS):
            if nombre in objeto.variables:
                return objeto.variables[nombre]

            if nombre in objeto.acciones:
                return AccionEnlazada(
                    objeto.acciones[nombre],
                    modulo=objeto
                )

            raise ErrorEjecucionJARVIS(
                f"El modulo '{objeto.nombre}' "
                f"no contiene '{nombre}'"
            )

        # Se consultan valores de enumeraciones.
        if (
            isinstance(objeto, dict)
            and "__enumeracion__" in objeto
        ):
            if nombre not in objeto["__enumeracion__"]:
                raise ErrorEjecucionJARVIS(
                    f"La enumeracion no contiene '{nombre}'"
                )

            return objeto["__enumeracion__"][nombre]

        raise ErrorEjecucionJARVIS(
            "El acceso por punto requiere objeto o modulo"
        )

    def _crear_objeto(
        self,
        nombre: str,
        valores: list[Any]
    ) -> InstanciaJARVIS:
        # Se crea una instancia y se inicializan sus atributos.
        # Las estructuras tambien se pueden construir con CREAR.
        if nombre in self.estructuras:
            campos = self.estructuras[nombre].get("campos", [])

            if len(campos) != len(valores):
                raise ErrorEjecucionJARVIS(
                    f"La estructura '{nombre}' requiere "
                    f"{len(campos)} valor(es), pero recibio {len(valores)}"
                )

            objeto = InstanciaJARVIS(nombre)

            for campo, valor in zip(campos, valores):
                nombre_campo = campo["nombre"]
                tipo_campo = campo["tipo"]

                objeto.atributos[nombre_campo] = self._normalizar(
                    tipo_campo, valor, nombre_campo
                )
                objeto.metadatos[nombre_campo] = {
                    "tipo": tipo_campo,
                    "clase": "var",
                    "visibilidad": "publico",
                    "origen": nombre,
                }

            return objeto

        if nombre not in self.clases:
            raise ErrorEjecucionJARVIS(
                f"La clase '{nombre}' no existe"
            )

        objeto = InstanciaJARVIS(nombre)

        objeto_anterior = self._objeto_actual
        clase_anterior = self._clase_actual

        try:
            self._objeto_actual = objeto

            for clase in self._jerarquia(nombre):
                self._clase_actual = clase["nombre"]

                for miembro in clase["miembros"]:
                    if miembro["tipo"] != "variable":
                        continue

                    campo = miembro["nombre"]

                    if campo in objeto.atributos:
                        continue

                    expresion = miembro.get("valor")

                    valor = (
                        self.evaluar(expresion)
                        if expresion is not None
                        else None
                    )

                    tipo = (
                        miembro.get("dato")
                        or self._tipo_valor(valor)
                    )

                    objeto.atributos[campo] = (
                        self._normalizar(tipo, valor, campo)
                        if valor is not None
                        else None
                    )

                    objeto.metadatos[campo] = {
                        "tipo": tipo,
                        "clase": miembro.get("clase", "var"),
                        "visibilidad": miembro.get(
                            "visibilidad",
                            "publico"
                        ),
                        "origen": clase["nombre"]
                    }

        finally:
            self._objeto_actual = objeto_anterior
            self._clase_actual = clase_anterior

        # Se busca la accion que inicializa el objeto.
        iniciador: AccionEnlazada | None = None

        for clase in self._jerarquia(
            nombre,
            inversa=True
        ):
            for miembro in clase["miembros"]:
                if (
                    miembro["tipo"] == "accion"
                    and miembro["nombre"] == "iniciar"
                ):
                    iniciador = AccionEnlazada(
                        miembro,
                        objeto=objeto,
                        clase=clase["nombre"]
                    )
                    break

            if iniciador:
                break

        if iniciador is not None:
            self._llamar(iniciador, valores)

        elif valores:
            raise ErrorEjecucionJARVIS(
                f"La clase '{nombre}' no admite argumentos"
            )

        return objeto

    def ejecutar_accion(
        self,
        nombre: str,
        argumentos: list[Any] | None = None,
        evaluados: bool = False
    ) -> Any:
        # Se ejecuta una accion global.
        if nombre not in self.acciones:
            raise ErrorEjecucionJARVIS(
                f"La accion '{nombre}' no existe"
            )

        origen = [] if argumentos is None else argumentos

        valores = (
            origen
            if evaluados
            else [
                self.evaluar(argumento)
                for argumento in origen
            ]
        )

        return self._llamar(
            AccionEnlazada(self.acciones[nombre]),
            valores
        )

    def _llamar(
        self,
        enlace: AccionEnlazada,
        valores: list[Any]
    ) -> Any:
        # Se verifica la cantidad de argumentos de la accion.
        accion = enlace.accion
        parametros = accion.get("parametros", [])

        if len(parametros) != len(valores):
            raise ErrorEjecucionJARVIS(
                f"La accion '{accion['nombre']}' espera "
                f"{len(parametros)} argumento(s)"
            )

        if len(self.pila_acciones) >= self.MAX_LLAMADAS:
            raise ErrorEjecucionJARVIS(
                "Limite de llamadas superado"
            )

        # Se conserva el contexto del llamador.
        ambitos_previos = self._ambitos
        metadatos_previos = self._metadatos

        objeto_previo = self._objeto_actual
        clase_previa = self._clase_actual

        # Se separan las variables locales del llamador.
        self._ambitos = [self.variables]
        self._metadatos = [metadatos_previos[0]]

        if enlace.modulo is not None:
            self._ambitos.append(
                enlace.modulo.variables
            )

            self._metadatos.append(
                enlace.modulo.metadatos
            )

        self._objeto_actual = enlace.objeto
        self._clase_actual = enlace.clase

        self.pila_acciones.append(
            accion["nombre"]
        )

        retorno: Any = None

        try:
            with self._ambito():
                # Se registran los parametros.
                for parametro, valor in zip(
                    parametros,
                    valores
                ):
                    self._declarar(
                        parametro["nombre"],
                        valor,
                        parametro["tipo"],
                        "parametro"
                    )

                # Se ejecutan las instrucciones.
                try:
                    self._ejecutar_bloque(
                        accion["instrucciones"],
                        nuevo_ambito=False
                    )

                except _Devolver as resultado:
                    retorno = resultado.valor

            esperado = (
                accion.get("retorno")
                or "vacio"
            )

            if esperado != "vacio" and retorno is None:
                raise ErrorEjecucionJARVIS(
                    f"La accion '{accion['nombre']}' "
                    "no devolvio valor"
                )

            if esperado != "vacio":
                retorno = self._normalizar(
                    esperado,
                    retorno,
                    accion["nombre"]
                )

            return retorno

        finally:
            # Se restaura el contexto anterior.
            self.pila_acciones.pop()

            self._ambitos = ambitos_previos
            self._metadatos = metadatos_previos

            self._objeto_actual = objeto_previo
            self._clase_actual = clase_previa

    def _integrada(
        self,
        nombre: str,
        argumentos: list[Any]
    ) -> Any:
        # Se ejecutan las funciones integradas.
        if nombre == "checar":
            if len(argumentos) != 1:
                raise ErrorEjecucionJARVIS(
                    "checar requiere un argumento"
                )

            return bool(argumentos[0])

        if nombre == "preguntar":
            if len(argumentos) > 1:
                raise ErrorEjecucionJARVIS(
                    "preguntar admite un argumento como maximo"
                )

            mensaje = (
                self.convertir_salida(argumentos[0])
                if argumentos
                else ""
            )

            if self.proveedor_entrada is not None:
                return str(
                    self.proveedor_entrada(mensaje)
                )

            if not sys.stdin or not sys.stdin.isatty():
                raise ErrorEjecucionJARVIS(
                    "preguntar requiere entrada desde la interfaz"
                )

            return input(mensaje)

        raise ErrorEjecucionJARVIS(
            f"Funcion integrada desconocida: {nombre}"
        )

    def _compuesto(
        self,
        actual: Any,
        operador: str,
        nuevo: Any
    ) -> Any:
        # Se resuelven las asignaciones compuestas.
        if operador == "+=":
            return actual + nuevo

        if operador == "-=":
            return actual - nuevo

        if operador == "*=":
            return actual * nuevo

        if operador == "/=":
            return actual / nuevo

        raise ErrorEjecucionJARVIS(
            f"Operador desconocido: {operador}"
        )

    def _escribir(
        self,
        objetivo: dict[str, Any],
        operador: str,
        nuevo: Any
    ) -> None:
        # Se comprueba que la variable original no sea constante.
        raiz = objetivo

        while raiz.get("tipo") in ("indice", "atributo"):
            raiz = raiz["objeto"]

        if raiz.get("tipo") == "identificador":
            nombre_raiz = raiz["nombre"]
            _, metas = self._buscar(nombre_raiz)

            if (
                metas.get(nombre_raiz, {}).get("clase")
                == "fijo"
            ):
                raise ErrorEjecucionJARVIS(
                    f"No se puede modificar "
                    f"la constante '{nombre_raiz}'"
                )

        tipo = objetivo["tipo"]

        # Se modifica una variable.
        if tipo == "identificador":
            nombre = objetivo["nombre"]

            if operador != "=":
                nuevo = self._compuesto(
                    self.evaluar(objetivo),
                    operador,
                    nuevo
                )

            self._asignar_nombre(nombre, nuevo)
            return

        # Se modifica un elemento de una coleccion.
        if tipo == "indice":
            contenedor: Any = self.evaluar(
                objetivo["objeto"]
            )

            indice: Any = self.evaluar(
                objetivo["indice"]
            )

            if not isinstance(contenedor, (list, dict)):
                raise ErrorEjecucionJARVIS(
                    "La asignacion requiere una lista o mapa"
                )

            try:
                if isinstance(contenedor, list):
                    if (
                        type(indice) is not int
                        or not -len(contenedor) <= indice < len(contenedor)
                    ):
                        raise ErrorEjecucionJARVIS(
                            "Indice de lista no valido"
                        )

                elif not isinstance(indice, Hashable):
                    raise ErrorEjecucionJARVIS(
                        "Clave de mapa no valida"
                    )

                if operador != "=":
                    nuevo = self._compuesto(
                        contenedor[indice],
                        operador,
                        nuevo
                    )

                base = objetivo["objeto"]

                # Se comprueba el tipo de la coleccion.
                if base.get("tipo") == "identificador":
                    _, metas = self._buscar(
                        base["nombre"]
                    )

                    tipo_base = metas.get(
                        base["nombre"],
                        {}
                    ).get("tipo")

                    if isinstance(tipo_base, dict):
                        if tipo_base.get("tipo") == "lista":
                            nuevo = self._normalizar(
                                tipo_base["elemento"],
                                nuevo,
                                base["nombre"]
                            )

                        elif tipo_base.get("tipo") == "mapa":
                            self._normalizar(
                                tipo_base["clave"],
                                indice,
                                base["nombre"]
                            )

                            nuevo = self._normalizar(
                                tipo_base["valor"],
                                nuevo,
                                base["nombre"]
                            )

                contenedor[indice] = nuevo

            except (
                IndexError,
                KeyError,
                TypeError
            ) as error:
                raise ErrorEjecucionJARVIS(
                    "No se pudo escribir ese elemento"
                ) from error

            self._comprobar_vigilancias()
            return

        # Se modifica un atributo de objeto o modulo.
        if tipo == "atributo":
            objeto = self.evaluar(
                objetivo["objeto"]
            )

            nombre = objetivo["nombre"]

            if isinstance(objeto, InstanciaJARVIS):
                if nombre not in objeto.atributos:
                    raise ErrorEjecucionJARVIS(
                        f"El atributo '{nombre}' no existe"
                    )

                datos = objeto.metadatos.get(
                    nombre,
                    {}
                )

                if datos.get("clase") == "fijo":
                    raise ErrorEjecucionJARVIS(
                        f"No se puede modificar "
                        f"la constante '{nombre}'"
                    )

                if (
                    datos.get("visibilidad") == "privado"
                    and self._clase_actual != datos.get("origen")
                ):
                    raise ErrorEjecucionJARVIS(
                        f"El atributo '{nombre}' es privado"
                    )

                if operador != "=":
                    nuevo = self._compuesto(
                        objeto.atributos[nombre],
                        operador,
                        nuevo
                    )

                objeto.atributos[nombre] = self._normalizar(
                    datos.get("tipo"),
                    nuevo,
                    nombre
                )

            elif isinstance(objeto, ModuloJARVIS):
                if nombre not in objeto.variables:
                    raise ErrorEjecucionJARVIS(
                        f"El modulo no contiene '{nombre}'"
                    )

                datos = objeto.metadatos.get(
                    nombre,
                    {}
                )

                if datos.get("clase") == "fijo":
                    raise ErrorEjecucionJARVIS(
                        f"No se puede modificar "
                        f"la constante '{nombre}'"
                    )

                if operador != "=":
                    nuevo = self._compuesto(
                        objeto.variables[nombre],
                        operador,
                        nuevo
                    )

                objeto.variables[nombre] = self._normalizar(
                    datos.get("tipo"),
                    nuevo,
                    nombre
                )

            else:
                raise ErrorEjecucionJARVIS(
                    "El destino no tiene atributos modificables"
                )

            self._comprobar_vigilancias()
            return

        raise ErrorEjecucionJARVIS(
            "Destino de asignacion invalido"
        )

    def _registrar_vigilancia(
        self,
        instruccion: dict[str, Any]
    ) -> None:
        # Se registra una condicion observable.
        vigilancia: dict[str, Any] = {
            "condicion": instruccion["condicion"],
            "instrucciones": instruccion["instrucciones"],
            "ultimo": False
        }

        try:
            actual = self.evaluar(
                instruccion["condicion"]
            )

            if type(actual) is not bool:
                raise TypeError(
                    "VIGILAR requiere una condicion logica"
                )

            vigilancia["ultimo"] = actual

        except ErrorEjecucionJARVIS:
            vigilancia["ultimo"] = False

        self.vigilancias.append(vigilancia)

    def _comprobar_vigilancias(self) -> None:
        # Se detectan los cambios de falso a verdadero.
        if self._vigilando or not self.vigilancias:
            return

        self._vigilando = True

        try:
            for vigilancia in list(self.vigilancias):
                actual = self.evaluar(
                    vigilancia["condicion"]
                )

                if type(actual) is not bool:
                    raise TypeError(
                        "VIGILAR requiere una condicion logica"
                    )

                anterior = vigilancia["ultimo"]
                vigilancia["ultimo"] = actual

                if actual and not anterior:
                    self._ejecutar_bloque(
                        vigilancia["instrucciones"]
                    )

        finally:
            self._vigilando = False

    def _ejecutar_bloque(
        self,
        instrucciones: list[dict[str, Any]],
        nuevo_ambito: bool = True
    ) -> None:
        # Se ejecutan las instrucciones dentro de su ambito.
        if nuevo_ambito:
            with self._ambito():
                for instruccion in instrucciones:
                    self.ejecutar_instruccion(instruccion)

        else:
            for instruccion in instrucciones:
                self.ejecutar_instruccion(instruccion)

    def ejecutar_instruccion(
        self,
        instruccion: dict[str, Any]
    ) -> None:
        tipo = instruccion["tipo"]

        # Se declara una variable.
        if tipo == "variable":
            expresion = instruccion.get("valor")

            valor = (
                self.evaluar(expresion)
                if expresion is not None
                else None
            )

            self._declarar(
                instruccion["nombre"],
                valor,
                instruccion.get("dato"),
                instruccion.get("clase", "var")
            )
            return

        # Se realiza una asignacion.
        if tipo == "asignacion":
            objetivo = instruccion.get("objetivo") or {
                "tipo": "identificador",
                "nombre": instruccion["nombre"]
            }

            self._escribir(
                objetivo,
                instruccion["operador"],
                self.evaluar(instruccion["valor"])
            )
            return

        # Se muestran mensajes.
        if tipo in ("imprimir", "alerta", "registrar"):
            argumentos = instruccion.get("argumentos")

            if argumentos is None:
                argumentos = [
                    instruccion.get("mensaje", "")
                ]

            texto = " ".join(
                self.convertir_salida(
                    self.evaluar(argumento)
                )
                for argumento in argumentos
            )

            prefijo = {
                "imprimir": "",
                "alerta": "ALERTA: ",
                "registrar": "REGISTRO: "
            }[tipo]

            print(prefijo + texto)
            return

        # Se ejecutan condiciones.
        if tipo == "si":
            condicion = self.evaluar(
                instruccion["condicion"]
            )

            if type(condicion) is not bool:
                raise TypeError(
                    "La condicion SI debe ser logica"
                )

            rama = (
                instruccion["instrucciones_si"]
                if condicion
                else instruccion["instrucciones_sino"]
            )

            self._ejecutar_bloque(rama)
            return

        # Se ejecuta una seleccion segun.
        if tipo == "segun":
            valor = self.evaluar(
                instruccion["valor"]
            )

            bloque = instruccion.get(
                "otro_caso",
                []
            )

            for caso in instruccion["casos"]:
                if valor == self.evaluar(caso["valor"]):
                    bloque = caso["instrucciones"]
                    break

            try:
                self._ejecutar_bloque(bloque)

            except _Detener:
                pass

            return

        # Se ejecuta una repeticion.
        if tipo == "repetir":
            veces = self.evaluar(
                instruccion["cantidad"]
            )

            if type(veces) is not int or veces < 0:
                raise ErrorEjecucionJARVIS(
                    "REPETIR requiere un entero no negativo"
                )

            if veces > self.MAX_ITERACIONES:
                raise ErrorEjecucionJARVIS(
                    "Limite de iteraciones superado"
                )

            for _ in range(veces):
                try:
                    self._ejecutar_bloque(
                        instruccion["instrucciones"]
                    )

                except _Seguir:
                    continue

                except _Detener:
                    break

            return

        # Se ejecuta un ciclo mientras.
        if tipo == "mientras":
            for vuelta in range(
                self.MAX_ITERACIONES + 1
            ):
                condicion = self.evaluar(
                    instruccion["condicion"]
                )

                if type(condicion) is not bool:
                    raise TypeError(
                        "MIENTRAS requiere una condicion logica"
                    )

                if not condicion:
                    return

                if vuelta == self.MAX_ITERACIONES:
                    raise ErrorEjecucionJARVIS(
                        "MIENTRAS supero el limite de iteraciones"
                    )

                try:
                    self._ejecutar_bloque(
                        instruccion["instrucciones"]
                    )

                except _Seguir:
                    continue

                except _Detener:
                    break

            return

        # Se ejecutan los ciclos para.
        if tipo in ("para", "para_en"):
            with self._ambito():
                if tipo == "para_en":
                    coleccion = self.evaluar(
                        instruccion["coleccion"]
                    )

                    if not isinstance(coleccion, (list, dict)):
                        raise ErrorEjecucionJARVIS(
                            "PARA EN requiere una lista o mapa"
                        )

                    iterador = instruccion["iterador"]

                    if iterador["declarar"]:
                        self._declarar(
                            iterador["nombre"],
                            None,
                            "cualquiera"
                        )

                    for posicion, valor in enumerate(
                        list(coleccion)
                    ):
                        if posicion >= self.MAX_ITERACIONES:
                            raise ErrorEjecucionJARVIS(
                                "PARA EN supero el limite de iteraciones"
                            )

                        self._asignar_nombre(
                            iterador["nombre"],
                            valor
                        )

                        try:
                            self._ejecutar_bloque(
                                instruccion["instrucciones"]
                            )

                        except _Seguir:
                            continue

                        except _Detener:
                            break

                    return

                # Se prepara la inicializacion del contador.
                inicio = instruccion.get("inicio")

                if inicio is not None:
                    self.ejecutar_instruccion(inicio)

                for vuelta in range(
                    self.MAX_ITERACIONES + 1
                ):
                    condicion = self.evaluar(
                        instruccion["condicion"]
                    )

                    if type(condicion) is not bool:
                        raise TypeError(
                            "PARA requiere una condicion logica"
                        )

                    if not condicion:
                        return

                    if vuelta == self.MAX_ITERACIONES:
                        raise ErrorEjecucionJARVIS(
                            "PARA supero el limite de iteraciones"
                        )

                    try:
                        self._ejecutar_bloque(
                            instruccion["instrucciones"]
                        )

                    except _Seguir:
                        pass

                    except _Detener:
                        break

                    cambio = instruccion.get("cambio")

                    if cambio is not None:
                        self.ejecutar_instruccion(cambio)

            return

        # Se controlan los saltos de los ciclos.
        if tipo == "detener":
            raise _Detener()

        if tipo == "seguir":
            raise _Seguir()

        # Se devuelve un valor desde una accion.
        if tipo == "devolver":
            valor = instruccion.get("valor")

            raise _Devolver(
                self.evaluar(valor)
                if valor is not None
                else None
            )

        # Se ejecutan misiones secundarias.
        if tipo == "ejecutar":
            nombre = instruccion["nombre"]

            if nombre not in self.misiones:
                raise ErrorEjecucionJARVIS(
                    f"La mision '{nombre}' no existe"
                )

            if self._contador_misiones >= self.MAX_LLAMADAS:
                raise ErrorEjecucionJARVIS(
                    "Limite de misiones superado"
                )

            self._contador_misiones += 1

            try:
                self._ejecutar_bloque(
                    self.misiones[nombre]["instrucciones"]
                )

            finally:
                self._contador_misiones -= 1

            return

        # Se ejecutan los bloques de manejo de errores.
        if tipo == "proteger":
            try:
                self._ejecutar_bloque(
                    instruccion["instrucciones"]
                )

            except (_Devolver, _Detener, _Seguir):
                raise

            except Exception as error:
                capturador = instruccion.get("atrapar")

                if capturador is None:
                    raise

                with self._ambito():
                    self._declarar(
                        capturador["nombre"],
                        str(error),
                        "cadenita"
                    )

                    self._ejecutar_bloque(
                        capturador["instrucciones"],
                        nuevo_ambito=False
                    )

            finally:
                self._ejecutar_bloque(
                    instruccion.get("finalmente", [])
                )

            return

        # Se genera un error controlado.
        if tipo == "lanzar":
            raise ErrorEjecucionJARVIS(
                self.convertir_salida(
                    self.evaluar(instruccion["valor"])
                )
            )

        # Se registra una vigilancia.
        if tipo == "vigilar":
            self._registrar_vigilancia(instruccion)
            return

        # Se ejecutan expresiones independientes.
        if tipo in (
            "llamada",
            "identificador",
            "indice",
            "atributo",
            "crear",
            "operacion",
            "comparacion",
            "logica",
            "unario",
            "lista",
            "mapa",
            "cadena",
            "caracter",
            "nada"
        ):
            self.evaluar(instruccion)
            return

        raise ErrorEjecucionJARVIS(
            f"Instruccion no implementada: {tipo}"
        )

    def _preparar(
        self,
        arbol: dict[str, Any]
    ) -> None:
        # Se reinicia el estado entre ejecuciones.
        self.variables.clear()
        self.acciones.clear()
        self.pila_acciones.clear()

        self._ambitos = [self.variables]
        self._metadatos = [{}]

        self._objeto_actual = None
        self._clase_actual = None

        self.vigilancias.clear()
        self._vigilando = False
        self._contador_misiones = 0

        self.registrar_acciones(arbol)

        # Se registran las misiones disponibles.
        self.misiones = {
            mision["nombre"]: mision
            for mision in arbol.get("misiones", [])
        }

        self.misiones["principal"] = arbol["mision"]

        definiciones = arbol.get(
            "definiciones",
            []
        )

        # Se registran las clases.
        self.clases = {
            definicion["nombre"]: definicion
            for definicion in definiciones
            if definicion["tipo"] == "clase"
        }

        # Se registran las estructuras.
        self.estructuras = {
            definicion["nombre"]: definicion
            for definicion in definiciones
            if definicion["tipo"] == "estructura"
        }

        # Se registran las enumeraciones.
        self.enumeraciones = {
            definicion["nombre"]: definicion
            for definicion in definiciones
            if definicion["tipo"] == "enumeracion"
        }

        # Se preparan los modulos.
        self.modulos = {
            definicion["nombre"]: ModuloJARVIS(
                definicion["nombre"]
            )
            for definicion in definiciones
            if definicion["tipo"] == "modulo"
        }

        # Se inicializan los valores de enumeraciones.
        for nombre, definicion in self.enumeraciones.items():
            valores = {
                elemento: EnumeracionJARVIS(
                    nombre,
                    elemento
                )
                for elemento in definicion["valores"]
            }

            self.variables[nombre] = {
                "__enumeracion__": valores
            }

            self._metadatos[0][nombre] = {
                "tipo": {
                    "tipo": "personalizado",
                    "nombre": nombre
                },
                "clase": "fijo"
            }

        # Se registran las referencias a modulos.
        for nombre, modulo in self.modulos.items():
            self.variables[nombre] = modulo

            self._metadatos[0][nombre] = {
                "tipo": {
                    "tipo": "personalizado",
                    "nombre": nombre
                },
                "clase": "fijo"
            }

        # Se preparan las acciones y variables de los modulos.
        for definicion in definiciones:
            if definicion["tipo"] != "modulo":
                continue

            modulo = self.modulos[
                definicion["nombre"]
            ]

            for elemento in definicion.get("elementos", []):
                if elemento["tipo"] == "accion":
                    modulo.acciones[
                        elemento["nombre"]
                    ] = elemento

            with self._ambito():
                self._ambitos[-1] = modulo.variables
                self._metadatos[-1] = modulo.metadatos

                for elemento in definicion.get("elementos", []):
                    if elemento["tipo"] == "variable":
                        self.ejecutar_instruccion(elemento)

        # Se inicializan las variables globales.
        for declaracion in arbol.get("globales", []):
            self.ejecutar_instruccion(declaracion)

        # Se registran las vigilancias globales.
        for vigilancia in arbol.get("vigilancias", []):
            self._registrar_vigilancia(vigilancia)

    def ejecutar_programa(
        self,
        arbol: dict[str, Any]
    ) -> None:
        # Se ejecuta la mision principal.
        self._preparar(arbol)

        print("========== JARVIS ==========")
        print("Sistema:", arbol["nombre"])
        print("Ejecutando mision principal...")
        print()

        try:
            # Se conservan las variables principales para la GUI.
            self._ejecutar_bloque(
                arbol["mision"]["instrucciones"],
                nuevo_ambito=False
            )

        except (_Devolver, _Seguir, _Detener) as error:
            raise ErrorEjecucionJARVIS(
                "Instruccion de control fuera "
                "de su contexto permitido"
            ) from error

        print()
        print("Mision finalizada correctamente")


if __name__ == "__main__":
    try:
        # Se analiza el programa de ejemplo.
        lexer.lineno = 1

        arbol = parser.parse(
            codigo,
            lexer=lexer
        )

        if arbol is None:
            raise SyntaxError(
                "No se pudo construir el AST"
            )

        # Se realiza el analisis semantico.
        analizar_programa(arbol)

        # Se ejecuta el programa.
        ejecutor = EjecutorJARVIS()
        ejecutor.ejecutar_programa(arbol)

        print(
            "Energia final:",
            ejecutor.variables.get("energia")
        )

    except (
        SyntaxError,
        ErrorSemantico,
        ValueError,
        TypeError,
        ZeroDivisionError,
        RecursionError,
        OverflowError
    ) as error:
        print("========== ERROR JARVIS ==========")
        print(error)

