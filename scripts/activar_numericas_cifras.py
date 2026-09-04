"""Activa columnas_numericas en el perfil de Cifras Nacionales 2025
(bump a v2): en cada hoja de datos, las columnas se renombran desde
la fila sub (los nombres de métrica) y se declaran numéricas las
que su muestreo de datos sea >= 80% parseable.
Uso: PYTHONPATH=. python3 scripts/activar_numericas_cifras.py
"""
import json
import sys

from infosalud.datos import _a_numero
from infosalud.estructura import leer_filas
from infosalud.perfiles import cargar, guardar, ruta_perfil, validar

ID = "estadisticas-nacionales-cifras-2025"
CATALOGO = "data/fuentes.json"
FECHA = "2026-09-04"


def main():
    catalogo = json.load(open(CATALOGO, encoding="utf-8"))
    fuente = next(f for f in catalogo["fuentes"] if f["id"] == ID)
    ver = fuente["verificaciones"][-1]
    hojas_leidas = {h["hoja"]: h["filas"]
                    for h in leer_filas(ver["ruta_local"],
                                        max_filas=200000)}
    ruta = ruta_perfil(CATALOGO, ID)
    perfil = cargar(ruta)
    perfil["version_perfil"] = 2
    perfil["fecha"] = FECHA
    for hoja in perfil["hojas"]:
        if hoja.get("tipo") != "datos" \
                or "filas_datos" not in hoja:
            continue
        filas = hojas_leidas[hoja["nombre"]]
        rango = hoja["filas_datos"]
        datos = filas[rango["desde"] - 1:rango["hasta"]]
        # Renombrar columnas desde la fila sub (nombres de métrica).
        if hoja.get("fila_encabezados_sub"):
            sub = hoja["fila_encabezados_sub"]
            hoja["columnas"] = filas[sub - 1]
        hoja.pop("clave_primaria", None)  # vive en la fila de grupo
        columnas = hoja["columnas"]
        numericas = []
        for i, columna in enumerate(columnas):
            if not columna.strip():
                continue
            valores = [fila[i] for fila in datos
                       if i < len(fila)]
            parseables = sum(1 for v in valores
                             if _a_numero(v) is not None)
            if valores and parseables / len(valores) >= 0.8:
                numericas.append(columna)
        if numericas:
            hoja["columnas_numericas"] = numericas
        print(f"  {hoja['nombre']}: {len(numericas)} numéricas de "
              f"{len(columnas)}")
    perfil["notas"] = ("Encabezado compuesto: fila de grupo + fila "
                       "sub. Totales (Nacional / Total Delegaciones "
                       "/ Total OOAD) en filas_total; fila '**' en "
                       "filas_nota. v2: columnas renombradas desde "
                       "la fila sub y columnas numéricas por "
                       "muestreo (>= 80% parseable).")
    errores = validar(perfil)
    if errores:
        print("INVALIDO:", errores)
        return 1
    guardar(ruta, perfil)
    print("OK ->", ruta)
    return 0


if __name__ == "__main__":
    sys.exit(main())
