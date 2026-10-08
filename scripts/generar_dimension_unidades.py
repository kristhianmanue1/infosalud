"""Generador de la dimension canonica `unidades` (ADR-016).

Proyecta el maestro de unidades desde el corte CUUMSP verificado
mas fresco y declara la entrada 'unidades' en
data/dimensiones.json. Fail-closed (ronda adversarial 2026-10-08):
- H-1: verifica unicidad de la Clave Presupuestal antes de declarar.
- H-2: resuelve nombres de columna verbatim desde el perfil.
- H-6: cualquier atributo ausente es error.
- M-2: re-verifica ausencia de subtotales.
Ademas calcula y reporta la cobertura contra el IFU convertido y la
Poblacion Adscrita verificados mas frescos (H-5: registro, no API).
Uso: PYTHONPATH=. python3 scripts/generar_dimension_unidades.py
"""
import json
import sys

from infosalud.estructura import leer_filas
from infosalud.exportar import MAX_FILAS
from infosalud.dimensiones import construir, cargar_config, ruta_config

CATALOGO = "data/fuentes.json"
ATRIBUTOS_DESEADOS = [
    "CLUES  Salud",
    "Clave Delegación o UMAE",
    "Nombre Delegación o UMAE",
    "Denominación Unidad",
    "Nombre Unidad",
    "Nivel de Atención",
    "Tipo de Servicio",
    "Descripción Tipo Servicio",
    "Entidad Federativa",
    "Clave Municipio o Delegación",
    "Municipio o Delegación",
    "Código postal",
    "LATITUD",
    "LONGITUD",
    "Grado de Marginación",
]
CLAVE = "Clave Presupuestal"


def fuente_cuumsp_mas_fresco(catalogo, forzada=None):
    if forzada:
        return forzada
    candidatos = []
    for f in catalogo["fuentes"]:
        if f["id"].startswith("recursos-cuumsp-") \
                and f.get("formato") == "xlsx" \
                and f.get("verificaciones"):
            candidatos.append((f["verificaciones"][-1]["fecha"],
                               f["id"]))
    if not candidatos:
        raise SystemExit("sin fuentes CUUMSP xlsx verificadas")
    return max(candidatos)[1]


def ruta_local(catalogo, id_fuente):
    f = next(x for x in catalogo["fuentes"] if x["id"] == id_fuente)
    return f["verificaciones"][-1]["ruta_local"]


def claves_presupuestales(ruta, hoja, col, desde, hasta):
    filas = {x["hoja"]: x["filas"] for x in
             leer_filas(ruta, max_filas=MAX_FILAS)}[hoja]
    return {str(filas[r - 1][col]).strip()
            for r in range(desde, hasta + 1)}


def main():
    catalogo = json.load(open(CATALOGO, encoding="utf-8"))
    id_cuumsp = fuente_cuumsp_mas_fresco(
        catalogo,
        forzada=sys.argv[1] if len(sys.argv) > 1 else None)
    perfil = json.load(open(
        f"data/perfiles/{id_cuumsp}.json", encoding="utf-8"))
    um = next(h for h in perfil["hojas"]
              if h["nombre"] == "Unidad Médica")
    columnas = um["columnas"]

    # H-2/H-6: resolver nombres verbatim; cualquier falta es error
    def verbatim(deseado):
        hallados = [c for c in columnas
                    if c is not None and c.strip() == deseado]
        if len(hallados) != 1:
            raise SystemExit(
                f"columna '{deseado}': {len(hallados)} coincidencias")
        return hallados[0]

    clave = verbatim(CLAVE)
    atributos = [verbatim(a) for a in ATRIBUTOS_DESEADOS]

    # H-1/M-2: unicidad de la clave y sin subtotales en el dato real
    ver = next(f for f in catalogo["fuentes"]
               if f["id"] == id_cuumsp)["verificaciones"][-1]
    desde = um["filas_datos"]["desde"]
    hasta = um["filas_datos"]["hasta"]
    col_clave = columnas.index(clave)
    claves = claves_presupuestales(
        ver["ruta_local"], "Unidad Médica", col_clave, desde, hasta)
    n_filas = hasta - desde + 1
    if len(claves) != n_filas:
        raise SystemExit(
            f"H-1: {n_filas} filas pero {len(claves)} claves unicas")

    # declarar la entrada y validar de extremo a extremo
    ruta_cfg = ruta_config(CATALOGO)
    config = cargar_config(CATALOGO) or {"version": 1,
                                        "dimensiones": {}}
    config["dimensiones"]["unidades"] = {
        "fuente": id_cuumsp,
        "hoja": "Unidad Médica",
        "clave": clave,
        "atributos": atributos,
    }
    with open(ruta_cfg, "w", encoding="utf-8") as fh:
        json.dump(config, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    cuerpo = construir(CATALOGO, "unidades", id_cuumsp,
                       "Unidad Médica", clave, atributos)
    if cuerpo.get("atributos_omitidos"):
        raise SystemExit(f"H-6: {cuerpo['atributos_omitidos']}")
    if cuerpo["sin_clave"]:
        raise SystemExit(f"sin_clave={cuerpo['sin_clave']}")
    print(f"dimension 'unidades' declarada: fuente={id_cuumsp}, "
          f"total={cuerpo['total']}, "
          f"procedencia={cuerpo['procedencia']['fecha_verificacion']}")

    # H-5: cobertura contra las otras series (registro, no API)
    for id_otra, hoja_otra, col_otra, filas_otra in (
            ("recursos-ifu-nacional-agosto-2026-convertido",
             "Unidad", 7, range(18, 1602)),
            ("poblacion-adscrita-ago-2026", "Pob. Adsc.", 3,
             range(12, 1335))):
        ver_otra = next(f for f in catalogo["fuentes"]
                        if f["id"] == id_otra)["verificaciones"][-1]
        otras = claves_presupuestales(ver_otra["ruta_local"],
                                      hoja_otra, col_otra,
                                      filas_otra[0], filas_otra[-1])
        if id_otra.startswith("poblacion"):
            otras = {c for c in otras if c[2:] != "0" * 10
                     and c != "000000000000"}
        fuera = sorted(otras - claves)
        print(f"cobertura {id_otra}: {len(otras & claves)}/"
              f"{len(otras)} dentro, {len(fuera)} fuera")


if __name__ == "__main__":
    main()
