"""Generador del arbol sintactico abstracto del lenguaje JARVIS.

Se representa el AST con Graphviz y se conserva el estilo azul original.
El resultado se guarda en arboles/AST_JARVIS_NUEVO.png.
"""

from pathlib import Path
from uuid import uuid4
from typing import Any

from graphviz import Digraph
from graphviz.backend import ExecutableNotFound


def _nombre_tipo(tipo: Any) -> str:
    """Se obtiene una descripcion legible de un tipo JARVIS."""
    if tipo is None:
        return "inferido"

    if not isinstance(tipo, dict):
        return str(tipo)

    clase = tipo.get("tipo")
    if clase == "personalizado":
        return str(tipo.get("nombre", "desconocido"))
    if clase == "lista":
        return f"lista[{_nombre_tipo(tipo.get('elemento'))}]"
    if clase == "mapa":
        return (
            f"mapa[{_nombre_tipo(tipo.get('clave'))}, "
            f"{_nombre_tipo(tipo.get('valor'))}]"
        )

    return str(clase or "desconocido")


def generar_ast(arbol: dict[str, Any]) -> str:
    """Se genera y se devuelve la ruta del PNG del AST de JARVIS."""
    if not isinstance(arbol, dict) or arbol.get("tipo") != "sistema":
        raise ValueError("Se requiere un AST de sistema JARVIS valido")

    grafico = Digraph("AST_JARVIS", format="png")
    grafico.attr(rankdir="TB")
    grafico.attr(
        "node",
        shape="box",
        style="rounded,filled",
        fillcolor="#DDEFFF",
        color="#2474A6",
        fontname="Arial",
    )

    contador = 0

    def nodo(texto: Any) -> str:
        nonlocal contador
        contador += 1
        identificador = str(contador)
        grafico.node(identificador, str(texto))
        return identificador

    def unir(padre: str, hijo: str, etiqueta: str = "") -> None:
        if etiqueta:
            grafico.edge(padre, hijo, label=etiqueta)
        else:
            grafico.edge(padre, hijo)

    def bloque(padre: str, nombre: str, instrucciones: Any) -> str:
        actual = nodo(nombre)
        unir(padre, actual)
        for instruccion in instrucciones or []:
            unir(actual, dibujar_instruccion(instruccion))
        return actual

    def valor(expresion: Any) -> str:
        # Se dibujan directamente los valores simples y logicos.
        if not isinstance(expresion, dict):
            if expresion is None:
                return nodo("Valor: nada")
            if expresion is True:
                return nodo("Valor: si paso")
            if expresion is False:
                return nodo("Valor: no paso")
            return nodo(f"Valor: {expresion}")

        tipo = expresion.get("tipo", "desconocido")

        if tipo == "identificador":
            return nodo(f"Identificador: {expresion.get('nombre')}")

        if tipo == "este":
            return nodo("Referencia: este")

        if tipo in ("cadena", "caracter"):
            return nodo(f"{tipo.capitalize()}: {expresion.get('valor')!r}")

        if tipo == "nada":
            return nodo("Valor: nada")

        if tipo in ("operacion", "comparacion", "logica"):
            actual = nodo(f"{tipo.capitalize()}: {expresion.get('operador')}")
            unir(actual, valor(expresion.get("izquierda")), "izq")
            unir(actual, valor(expresion.get("derecha")), "der")
            return actual

        if tipo == "unario":
            actual = nodo(f"Operador unario: {expresion.get('operador')}")
            unir(actual, valor(expresion.get("valor")), "valor")
            return actual

        if tipo == "lista":
            actual = nodo("Lista")
            for numero, elemento in enumerate(expresion.get("elementos", []), 1):
                unir(actual, valor(elemento), f"elemento {numero}")
            return actual

        if tipo == "mapa":
            actual = nodo("Mapa")
            for numero, par in enumerate(expresion.get("pares", []), 1):
                pareja = nodo(f"Par {numero}")
                unir(actual, pareja)
                unir(pareja, valor(par.get("clave")), "clave")
                unir(pareja, valor(par.get("valor")), "valor")
            return actual

        if tipo == "indice":
            actual = nodo("Acceso por indice")
            unir(actual, valor(expresion.get("objeto")), "coleccion")
            unir(actual, valor(expresion.get("indice")), "indice")
            return actual

        if tipo == "atributo":
            actual = nodo(f"Atributo: {expresion.get('nombre')}")
            unir(actual, valor(expresion.get("objeto")), "objeto")
            return actual

        if tipo == "llamada":
            nombre = expresion.get("nombre")
            actual = nodo(f"Llamada: {nombre or 'metodo'}()")
            objetivo = expresion.get("objetivo")
            if nombre is None and objetivo is not None:
                unir(actual, valor(objetivo), "destino")
            for numero, argumento in enumerate(expresion.get("argumentos", []), 1):
                unir(actual, valor(argumento), f"arg {numero}")
            return actual

        if tipo == "crear":
            actual = nodo(f"Crear: {expresion.get('clase')}")
            for numero, argumento in enumerate(expresion.get("argumentos", []), 1):
                unir(actual, valor(argumento), f"arg {numero}")
            return actual

        # Se conservan los detalles de los nodos futuros o no previstos.
        actual = nodo(f"Expresion: {tipo}")
        for clave, contenido in expresion.items():
            if clave == "tipo":
                continue
            if isinstance(contenido, dict):
                unir(actual, valor(contenido), clave)
            elif isinstance(contenido, list):
                for numero, elemento in enumerate(contenido, 1):
                    unir(actual, valor(elemento), f"{clave} {numero}")
            else:
                unir(actual, nodo(f"{clave}: {contenido}"))
        return actual

    def dibujar_accion(accion: dict[str, Any]) -> str:
        actual = nodo(f"Accion: {accion.get('nombre')}()")
        retorno = accion.get("retorno")
        if retorno is not None:
            unir(actual, nodo(f"Retorno: {_nombre_tipo(retorno)}"))
        for parametro in accion.get("parametros", []):
            unir(
                actual,
                nodo(
                    f"Parametro: {parametro.get('nombre')}\n"
                    f"Tipo: {_nombre_tipo(parametro.get('tipo'))}"
                ),
                "parametro",
            )
        bloque(actual, "Cuerpo de la accion", accion.get("instrucciones", []))
        return actual

    def dibujar_instruccion(datos: Any) -> str:
        if not isinstance(datos, dict):
            return valor(datos)

        tipo = datos.get("tipo", "desconocido")

        if tipo == "variable":
            clase = datos.get("clase", "var")
            actual = nodo(
                f"{clase.capitalize()}: {datos.get('nombre')}\n"
                f"Tipo: {_nombre_tipo(datos.get('dato'))}"
            )
            if datos.get("valor") is not None:
                unir(actual, valor(datos["valor"]), "valor")
            else:
                unir(actual, nodo("Sin inicializar"))
            return actual

        if tipo == "asignacion":
            actual = nodo(f"Asignacion: {datos.get('operador', '=')}")
            objetivo = datos.get("objetivo")
            if objetivo is None:
                objetivo = {"tipo": "identificador", "nombre": datos.get("nombre")}
            unir(actual, valor(objetivo), "destino")
            unir(actual, valor(datos.get("valor")), "valor")
            return actual

        if tipo in ("imprimir", "alerta", "registrar"):
            actual = nodo(tipo.capitalize())
            argumentos = datos.get("argumentos")
            if argumentos is None:
                argumentos = [datos.get("mensaje")]
            for numero, argumento in enumerate(argumentos, 1):
                unir(actual, valor(argumento), f"arg {numero}")
            return actual

        if tipo == "si":
            variante = datos.get("variante", "si")
            actual = nodo(f"Condicion {str(variante).upper()}")
            unir(actual, valor(datos.get("condicion")), "condicion")
            bloque(actual, "Bloque SI", datos.get("instrucciones_si", []))
            if datos.get("instrucciones_sino"):
                bloque(actual, "Bloque SINO / SINOSI", datos["instrucciones_sino"])
            return actual

        if tipo == "segun":
            actual = nodo("Seleccion SEGUN")
            unir(actual, valor(datos.get("valor")), "expresion")
            for caso in datos.get("casos", []):
                elemento = nodo("CASO")
                unir(actual, elemento)
                unir(elemento, valor(caso.get("valor")), "coincidencia")
                bloque(elemento, "Bloque CASO", caso.get("instrucciones", []))
            if datos.get("otro_caso"):
                bloque(actual, "OTRO CASO", datos["otro_caso"])
            return actual

        if tipo in ("repetir", "mientras", "para", "para_en"):
            actual = nodo(f"Ciclo {str(tipo).upper()}")
            if tipo == "repetir":
                unir(actual, valor(datos.get("cantidad")), "veces")
            if tipo == "mientras":
                unir(actual, valor(datos.get("condicion")), "condicion")
            if tipo == "para":
                if datos.get("inicio") is not None:
                    unir(actual, dibujar_instruccion(datos["inicio"]), "inicio")
                unir(actual, valor(datos.get("condicion")), "condicion")
                if datos.get("cambio") is not None:
                    unir(actual, dibujar_instruccion(datos["cambio"]), "cambio")
            if tipo == "para_en":
                iterador = datos.get("iterador", {})
                unir(actual, nodo(f"Iterador: {iterador.get('nombre')}"))
                unir(actual, valor(datos.get("coleccion")), "coleccion")
            bloque(actual, f"Bloque {str(tipo).upper()}", datos.get("instrucciones", []))
            return actual

        if tipo in ("detener", "seguir"):
            return nodo(tipo.capitalize())

        if tipo in ("devolver", "lanzar"):
            actual = nodo(tipo.capitalize())
            if datos.get("valor") is not None:
                unir(actual, valor(datos["valor"]), "valor")
            return actual

        if tipo == "ejecutar":
            return nodo(f"Ejecutar mision: {datos.get('nombre')}")

        if tipo == "proteger":
            actual = nodo("Manejo de errores: PROTEGER")
            bloque(actual, "Bloque PROTEGER", datos.get("instrucciones", []))
            capturador = datos.get("atrapar")
            if capturador:
                bloque(
                    actual,
                    f"ATRAPAR: {capturador.get('nombre')}",
                    capturador.get("instrucciones", []),
                )
            if datos.get("finalmente"):
                bloque(actual, "Bloque FINALMENTE", datos["finalmente"])
            return actual

        if tipo == "vigilar":
            actual = nodo("VIGILAR")
            unir(actual, valor(datos.get("condicion")), "condicion")
            bloque(actual, "Bloque VIGILAR", datos.get("instrucciones", []))
            return actual

        if tipo == "accion":
            return dibujar_accion(datos)

        if tipo == "mision":
            actual = nodo(f"Mision: {datos.get('nombre')}")
            bloque(actual, "Cuerpo de la mision", datos.get("instrucciones", []))
            return actual

        if tipo == "clase":
            actual = nodo(f"Clase: {datos.get('nombre')}")
            if datos.get("hereda"):
                unir(actual, nodo(f"Hereda: {datos['hereda']}"))
            for miembro in datos.get("miembros", []):
                hijo = dibujar_instruccion(miembro)
                unir(actual, hijo, miembro.get("visibilidad", "miembro"))
            return actual

        if tipo == "modulo":
            actual = nodo(f"Modulo: {datos.get('nombre')}")
            for elemento in datos.get("elementos", []):
                unir(actual, dibujar_instruccion(elemento))
            return actual

        if tipo == "estructura":
            actual = nodo(f"Estructura: {datos.get('nombre')}")
            for campo in datos.get("campos", []):
                unir(
                    actual,
                    nodo(
                        f"Campo: {campo.get('nombre')}\n"
                        f"Tipo: {_nombre_tipo(campo.get('tipo'))}"
                    ),
                )
            return actual

        if tipo == "enumeracion":
            actual = nodo(f"Enumeracion: {datos.get('nombre')}")
            for elemento in datos.get("valores", []):
                unir(actual, nodo(f"Valor: {elemento}"))
            return actual

        if tipo == "usar":
            return nodo(f"Importar modulo: {datos.get('ruta')}")

        # Se visualizan las expresiones utilizadas como instrucciones.
        if tipo in (
            "llamada", "identificador", "indice", "atributo", "crear",
            "operacion", "comparacion", "logica", "unario", "lista",
            "mapa", "cadena", "caracter", "nada", "este",
        ):
            return valor(datos)

        # Se dibuja un nodo generico para futuras extensiones.
        actual = nodo(f"Instruccion: {tipo}")
        for clave, contenido in datos.items():
            if clave == "tipo":
                continue
            if isinstance(contenido, dict):
                unir(actual, valor(contenido), clave)
            elif isinstance(contenido, list):
                for numero, elemento in enumerate(contenido, 1):
                    if isinstance(elemento, dict) and "tipo" in elemento:
                        hijo = dibujar_instruccion(elemento)
                    else:
                        hijo = valor(elemento)
                    unir(actual, hijo, f"{clave} {numero}")
            else:
                unir(actual, nodo(f"{clave}: {contenido}"))
        return actual

    raiz = nodo(f"Sistema: {arbol.get('nombre', 'Sin nombre')}")

    # Se respeta el orden original si el parser proporciona elementos.
    elementos = arbol.get("elementos")
    if elementos is None:
        elementos = [
            *arbol.get("globales", []),
            *arbol.get("definiciones", []),
            *arbol.get("acciones", []),
            *arbol.get("misiones", []),
        ]
        if arbol.get("mision") is not None:
            elementos.append(arbol["mision"])
        elementos.extend(arbol.get("vigilancias", []))

    for elemento in elementos:
        unir(raiz, dibujar_instruccion(elemento))

    carpeta = Path(__file__).resolve().parent / "arboles"
    carpeta.mkdir(parents=True, exist_ok=True)

    try:
        ruta = grafico.render(
            filename=f"AST_JARVIS_NUEVO_{uuid4().hex[:12]}",
            directory=str(carpeta),
            cleanup=True,
        )
    except ExecutableNotFound as error:
        raise RuntimeError(
            "Graphviz no encontro 'dot'. Se debe instalar Graphviz "
            "y agregar su carpeta bin al PATH del sistema."
        ) from error

    return str(Path(ruta).resolve())


if __name__ == "__main__":
    from alexico import lexer
    from asintactico import parser, codigo

    try:
        lexer.lineno = 1
        arbol = parser.parse(codigo, lexer=lexer)
        if arbol is None:
            raise SyntaxError("No se pudo construir el AST")
        ruta = generar_ast(arbol)
        print("========== JARVIS ==========")
        print("Analisis sintactico correcto")
        print("AST generado correctamente")
        print("Archivo guardado en:")
        print(ruta)
    except Exception as error:
        print("========== ERROR JARVIS ==========")
        print("Error al generar AST:")
        print(error)

