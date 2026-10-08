"""Sondeo del portal Infosalud (ADR-008; autorización PREGUNTA-1,
2026-10-08; cadencia quincenal vía launchd).

GET de sólo lectura a las páginas índice declaradas; extrae los
enlaces a archivos y reporta los que NO están registrados en
data/fuentes.json. Nunca muta el catálogo ni descarga binarios:
la integración de lo nuevo sigue siendo una decisión del operador
(o del agente, con autorización de la sesión).

Uso: PYTHONPATH=. python3 scripts/sondear_portal.py [--json]
Salida: informe en stdout + data/sondeos/<fecha>.json.
Códigos: 0 sin novedades; 3 con ediciones nuevas detectadas.
"""
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CATALOGO = RAIZ / "data" / "fuentes.json"
SONDEOS = RAIZ / "data" / "sondeos"
PAGINAS = [
    "http://infosalud.imss.gob.mx:8080/paginas/cuumsp2026.html",
    "http://infosalud.imss.gob.mx:8080/paginas/ifu_2026.html",
    "http://infosalud.imss.gob.mx:8080/PAGINAS/poblacion2026.html",
]
_PATRON = re.compile(r'href="([^"]+\.(?:xlsx|xlsb|xls|zip))"',
                     re.IGNORECASE)
_TIMEOUT = 20


def enlaces_de(pagina):
    with urllib.request.urlopen(pagina, timeout=_TIMEOUT) as r:
        html = r.read().decode("utf-8", "replace")
    base = urllib.parse.urljoin(pagina, ".")
    enlaces = set()
    for bruto in _PATRON.findall(html):
        absoluto = urllib.parse.urljoin(pagina, bruto)
        enlaces.add(urllib.parse.unquote(absoluto))
    return sorted(enlaces)


def urls_registradas():
    catalogo = json.loads(
        CATALOGO.read_text(encoding="utf-8"))
    return {urllib.parse.unquote(f["url"]).strip()
            for f in catalogo["fuentes"]}


def main():
    a_json = "--json" in sys.argv
    registradas = urls_registradas()
    informe = {"fecha": date.today().isoformat(), "paginas": [],
               "nuevos": []}
    for pagina in PAGINAS:
        try:
            enlaces = enlaces_de(pagina)
        except Exception as exc:  # noqa: BLE001 (sondeo: reportar)
            informe["paginas"].append(
                {"pagina": pagina, "error": str(exc)})
            continue
        nuevos = [u for u in enlaces if u not in registradas]
        informe["paginas"].append(
            {"pagina": pagina, "enlaces": len(enlaces),
             "nuevos": len(nuevos)})
        for url in nuevos:
            informe["nuevos"].append({"url": url, "pagina": pagina})
    SONDEOS.mkdir(exist_ok=True)
    destino = SONDEOS / f"{informe['fecha']}.json"
    destino.write_text(
        json.dumps(informe, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")
    if a_json:
        print(json.dumps(informe, ensure_ascii=False, indent=1))
    else:
        print(f"sondeo {informe['fecha']}: "
              f"{len(informe['nuevos'])} archivo(s) nuevo(s) "
              f"sin registrar; informe en {destino.name}")
        for nuevo in informe["nuevos"]:
            print(f"  NUEVO: {nuevo['url']}")
    return 3 if informe["nuevos"] else 0


if __name__ == "__main__":
    sys.exit(main())
