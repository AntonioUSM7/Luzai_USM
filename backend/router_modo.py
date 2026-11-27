import re
from typing import List

from router_jeff import normalizar

_PATRONES_PROCEDIMENTALES: List[str] = [
    r"\b(calcula|calcular|calculo|resuelve|resolver|resuelvo|configura|configurar|configuro|implementa|implementar|implemento|disena|disenar|diseno|realiza|realizar|realizo|ejecuta|ejecutar|ejecuto|arma|armar|armo|crea|crear|creo|monta|montar|monto)\b",
    r"\bcomo\s+(se\s+)?(configura|configurar|configuro|calcula|calcular|calculo|resuelve|resolver|resuelvo|implementa|implementar|implemento|disena|disenar|diseno|realiza|realizar|realizo|ejecuta|ejecutar|ejecuto|arma|armar|armo|crea|crear|creo|monta|montar|monto|aplica|aplicar|aplico|usa|usar|uso|utiliza|utilizar|utilizo|hace|hago|hacer)\b",
    r"\bdame\s+(el|los|la|las)?\s*(comando|comandos|codigo|configuracion|resultado|solucion|respuesta)\b",
    r"\bpaso\s+a\s+paso\b",
    r"\b(comando|comandos)\s+(para|de)\b",
    r"\b(cuanto\s+es|cuanto\s+da)\b",
]

_PATRONES_CONCEPTUALES: List[str] = [
    r"\b(que\s+es|que\s+son|explica|explicame|explicar|resume|resumen|define|definicion|describe|descripcion|diferencia|diferencias|compara|comparar|comparacion|concepto|intuicion|para\s+que\s+sirve|como\s+funciona|tipos\s+de|caracteristicas|ventajas|desventajas)\b",
    r"\b(que|cuales)\s+(protocolos|temas|contenidos|herramientas|tipos)\b",
]

_PATRONES_RESUMEN: List[str] = [
    r"\b(resume|resumen|resumir|temas|contenidos|protocolos)\b",
]


def detectar_modo(mensaje: str) -> str:
    """
    Clasifica la consulta en 'conceptual', 'procedimental' o 'general'.

    Es una heurística barata y determinista: no usa GPU. La prioridad es
    procedimental para no dar soluciones completas cuando el alumno pide
    calcular, configurar o implementar algo.
    """
    texto = normalizar(mensaje)
    if not texto:
        return "general"

    if any(re.search(patron, texto) for patron in _PATRONES_PROCEDIMENTALES):
        return "procedimental"

    if any(re.search(patron, texto) for patron in _PATRONES_CONCEPTUALES):
        return "conceptual"

    return "general"


def es_solicitud_resumen(mensaje: str) -> bool:
    """Indica si el alumno pide un resumen o un mapa de temas del ramo."""
    texto = normalizar(mensaje)
    return any(re.search(patron, texto) for patron in _PATRONES_RESUMEN)


_PATRONES_SALUDO: List[str] = [
    r"^(hola|holi|buenas|buenos dias|buenas tardes|buenas noches|hey|que tal|"
    r"como estas|como te va|gracias|muchas gracias|adios|chao|nos vemos)\b",
]

_PALABRAS_META: List[str] = [
    "tema", "temas", "materia", "contenido", "contenidos", "objetivo", "objetivos",
    "prueba", "examen", "certamen", "tarea", "laboratorio",
    "experiencia", "planificacion", "cronograma", "evaluacion", "presentacion",
    "fecha", "fechas", "paralelo",
    "ramo", "curso", "clase", "apunte", "apuntes", "profesor", "ayudante", "horario",
    "ejercicio", "ejercicios", "problema", "problemas", "guia", "guias",
    "pista", "pistas", "solucion", "resultado", "desarrollo",
]

_TERMINOS_TECNICOS: List[str] = [
    "subred", "mascara", "router", "enrutador", "switch", "vlan", "acl",
    "firewall", "stp", "protocolo", "protocolos", "integral", "derivada",
    "teorema", "superficie", "matriz", "vectorial", "campo vectorial",
    "ip", "tcp", "udp", "bgp", "rip", "ospf", "dhcp", "dns", "arp",
]

_PALABRAS_VACIAS = {
    "de", "la", "el", "los", "las", "y", "o", "en", "para", "con", "del", "al",
    "un", "una", "por", "que", "the", "and", "of",
}


def es_saludo(mensaje: str) -> bool:
    """Detecta saludos y agradecimientos para no tratarlos como fuera de foco."""
    texto = normalizar(mensaje).strip()
    return any(re.search(patron, texto) for patron in _PATRONES_SALUDO)


def menciona_tema_del_ramo(mensaje: str, temario: List[str]) -> bool:
    """Heurística de alcance: ¿la consulta menciona un tema o palabra meta del curso?"""
    texto = normalizar(mensaje)
    if re.search(r"\b(ot|exp|lab)\s*\d+\b", texto):
        return True

    if any(re.search(rf"\b{re.escape(palabra)}\b", texto) for palabra in _PALABRAS_META):
        return True

    if any(
        re.search(rf"\b{re.escape(termino)}\b", texto)
        if len(termino) <= 4
        else termino in texto
        for termino in _TERMINOS_TECNICOS
    ):
        return True

    terminos = set()
    for tema in temario:
        for palabra in re.findall(r"[a-z0-9]+", normalizar(tema)):
            if len(palabra) >= 2 and palabra not in _PALABRAS_VACIAS:
                terminos.add(palabra)

    for termino in terminos:
        if len(termino) <= 4:
            if re.search(rf"\b{re.escape(termino)}\b", texto):
                return True
        elif termino in texto:
            return True
    return False


_PATRONES_CALCULO_DIRECTO: List[str] = [
    r"\b(calcula|calcular|calculo|resuelve|resolver|resuelvo|dame\s+el\s+resultado|"
    r"cuanto\s+es|cuanto\s+da)\b",
]

_PATRONES_DATOS_CALCULO: List[str] = [
    r"\d\s*[/+\-*^=]\s*\d",
    r"\b\d{1,3}(?:\.\d{1,3}){3}\b",
    r"\b(integral|derivada|mascara|subred|matriz|ecuacion|area|perimetro|volumen|"
    r"raiz|logaritmo|limite|serie|probabilidad)\b",
]

_PATRON_COMO_CALCULA = r"\bcomo\s+(se\s+)?(calcula|calcular|resuelve|resolver)\b"


def es_calculo_directo(mensaje: str) -> bool:
    """Detecta peticiones de cálculo con datos suficientes para resolver."""
    texto = normalizar(mensaje)
    if re.search(_PATRON_COMO_CALCULA, texto):
        return False
    if not any(re.search(patron, texto) for patron in _PATRONES_CALCULO_DIRECTO):
        return False
    return any(re.search(patron, texto) for patron in _PATRONES_DATOS_CALCULO)


_PATRONES_ADMIN_PLANIFICACION: List[str] = [
    r"\b(experiencia|exp|laboratorio|lab)[\s_]*(?:n[°º]?\s*)?\d+\b",
    r"\b(clase|sesion|semana)\s*(?:n[°º]?\s*)?\d+\b",
    r"\b(ot\s*\d+|pres(?:entacion)?\s*\d+|certamen|evaluacion|evaluaciones|presentacion\s+(?:inicial|avance|final))\b",
    r"\b(planificacion|cronograma|calendario|fechas?\s+de|cuando\s+(?:es|son|se|toca|hay|entregan)|que\s+dia\s+(?:es|son|toca|hay))\b",
    r"\b(que\s+se\s+ve\s+en|que\s+entra\s+en|que\s+toca\s+en|que\s+pasa\s+en\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre))\b",
    r"\b(paralelo\s*20\d|fiestas\s+patrias|vacaciones|notas\s+finales|termino\s+de\s+(?:primer\s+)?semestre|feriado|holgura)\b",
]


_PATRONES_LOGISTICA_ESTRICTA: List[str] = [
    r"\b(planificacion|cronograma|calendario|fechas?|cuando\s+(?:es|son|se|toca|hay|entregan)|que\s+dia\s+(?:es|son|toca|hay))\b",
    r"\b(sala|horario|entrega|entregan|plazo|paralelo\s*20\d|fiestas\s+patrias|vacaciones|notas\s+finales|feriado|holgura)\b",
]

_PATRONES_CONTENIDO_ACADEMICO: List[str] = [
    r"\b(materia|contenido|contenidos|objetivo|objetivos|de\s+que\s+trata|explica|explicame|explicar|resume|resumen|resumir)\b",
    r"\b(como\s+se\s+hace|paso\s+a\s+paso|que\s+hay\s+que\s+hacer|ejercicios?|preguntas?|topologia|configura|configurar|configuracion|protocolo|protocolos)\b",
]


def es_consulta_contenido_academico(mensaje: str) -> bool:
    """Indica si el mensaje pide materia/contenido académico sin pedir fechas ni logística."""
    texto = normalizar(mensaje)
    if not texto:
        return False
    return any(re.search(patron, texto) for patron in _PATRONES_CONTENIDO_ACADEMICO) and not any(
        re.search(patron, texto) for patron in _PATRONES_LOGISTICA_ESTRICTA
    )


def es_consulta_administrativa_o_planificacion(mensaje: str) -> bool:
    """
    Detecta consultas sobre el cronograma, fechas, evaluaciones o mapa de sesiones/experiencias
    del curso, sin capturar preguntas puramente conceptuales, de contenido/materia o procedimentales técnicas.
    """
    texto = normalizar(mensaje)
    if not texto:
        return False
    if es_consulta_contenido_academico(mensaje):
        return False
    return any(re.search(patron, texto) for patron in _PATRONES_ADMIN_PLANIFICACION)
