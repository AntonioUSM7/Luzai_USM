"""Prueba rápida del enrutador Jeff. No necesita Ollama ni Docker."""

import json

import router_jeff

CASOS = [
    ("¿Cuándo es el certamen de MAT024?", "MAT024"),
    ("¿Qué libro recomienda el ramo?", "MAT024"),
    ("¿Cómo se entrega la tarea 1?", "MAT024"),
    ("¿Dónde es el laboratorio de TEL20425?", "TEL20425"),
    ("¿Cómo parametrizo la frontera de la semiesfera?", "MAT024"),
    ("ensalada de frutas", "TEL20425"),
]


def main() -> None:
    for mensaje, ramo in CASOS:
        resultado = router_jeff.resolver_consulta(mensaje, ramo)
        canal = resultado["canal"] if resultado else "TUTOR_SOCRATICO (deriva a RAG)"
        print(f"\n> {mensaje}  [{ramo}]")
        print(f"  canal: {canal}")
        if resultado:
            print(f"  topico: {resultado['topico']}")
            print(f"  respuesta: {resultado['respuesta']}")
        else:
            print(json.dumps(resultado, ensure_ascii=False))


if __name__ == "__main__":
    main()
