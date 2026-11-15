"""Pruebas rápidas del clasificador y de los guards. No necesita Ollama ni Docker."""

import sys

from router_modo import (
    detectar_modo,
    es_calculo_directo,
    es_saludo,
    menciona_tema_del_ramo,
)

CASOS_MODO = [
    ("¿Qué es una VLAN?", "conceptual"),
    ("Resume los protocolos vistos en el ramo", "conceptual"),
    ("¿Diferencia entre STP y RSTP?", "conceptual"),
    ("¿Cómo funciona el protocolo ARP?", "conceptual"),
    ("¿Qué protocolos se ven en el ramo?", "conceptual"),
    ("Explícame el teorema de Stokes", "conceptual"),
    ("¿Cómo configuro una VLAN en un switch?", "procedimental"),
    ("Calcula la máscara de subred para 192.168.1.0/24", "procedimental"),
    ("Dame el comando para crear una ACL", "procedimental"),
    ("¿Cómo se resuelve esta integral?", "procedimental"),
    ("Resuelve paso a paso el ejercicio 3", "procedimental"),
    ("¿Cuánto es 2+2?", "procedimental"),
    ("¿Cómo se calcula una máscara de subred?", "procedimental"),
    ("Hola", "general"),
]

CASOS_CALCULO = [
    ("Calcula la máscara de subred para 192.168.1.0/24", True),
    ("Calcula 2+2", True),
    ("Resuelve la integral de superficie de la semiesfera", True),
    ("Resuelve paso a paso el ejercicio 3", False),
    ("¿Cómo se calcula una máscara de subred?", False),
    ("¿Cuánto es 2+2?", True),
    ("Calcula el precio de 3 manzanas", False),
]

CASOS_SALUDO = [
    ("Hola", True),
    ("Gracias", True),
    ("¿Qué es una VLAN?", False),
]

TEMARIO = [
    "Cableado Estructurado",
    "Virtualizacion",
    "Spanning Tree Protocol",
    "VLAN",
    "Direccionamiento IP y Ruteo",
    "Ruteo Dinamico",
    "ACL",
    "Firewall",
    "Redes Inalambricas",
]

CASOS_ALCANCE = [
    ("¿Qué es una VLAN?", True),
    ("¿Qué es BGP?", True),
    ("Resuelve el ejercicio 3", True),
    ("Calcula la máscara de subred", True),
    ("¿Cuál es la capital de Francia?", False),
    ("Ensalada de frutas", False),
    ("¿Qué es una red neuronal?", False),
]


def ejecutar(nombre, casos, funcion):
    fallas = 0
    print(f"\n== {nombre} ==")
    for entrada, esperado in casos:
        obtenido = funcion(entrada)
        estado = "OK" if obtenido == esperado else "FALLA"
        if obtenido != esperado:
            fallas += 1
        print(f"[{estado}] {entrada!r} -> {obtenido} (esperado: {esperado})")
    return fallas


def main() -> None:
    fallas = 0
    fallas += ejecutar("Modo", CASOS_MODO, detectar_modo)
    fallas += ejecutar("Cálculo directo", CASOS_CALCULO, es_calculo_directo)
    fallas += ejecutar("Saludo", CASOS_SALUDO, es_saludo)
    fallas += ejecutar(
        "Alcance", CASOS_ALCANCE, lambda mensaje: menciona_tema_del_ramo(mensaje, TEMARIO)
    )

    if fallas:
        print(f"\n{fallas} caso(s) con falla.")
        sys.exit(1)

    print("\nTodos los casos pasaron.")


if __name__ == "__main__":
    main()
