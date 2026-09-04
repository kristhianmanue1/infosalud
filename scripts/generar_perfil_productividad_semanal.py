"""Perfil de PRODUCTIVIDAD POR SEMANA ESTADISTICA 2025
(ADR-014, SPEC-11). Hallazgo de la inspección: cada hoja tiene UNA
sola tabla con preámbulo (títulos/bloque de fechas) — el contrato
base (fila_encabezados + fila_encabezados_sub + filas_total +
filas_nota) la cubre sin necesidad de segmentos. Cada hoja trae
columna A vacía (posicional) y notas al final.
Uso: PYTHONPATH=. python3 scripts/generar_perfil_productividad_semanal.py
"""
import json
import sys

from infosalud.estructura import leer_filas
from infosalud.perfiles import guardar, ruta_perfil, validar

ID = "seguimiento-productividad-semanal-2025"
CATALOGO = "data/fuentes.json"
FECHA = "2026-09-04"

# (hoja, fila_encabezados, fila_sub, filas_total, desde, hasta, notas)
HOJAS = [
    ("Resumen Atenciones 2019-2025", 14, 15, [16], 17, 76,
     [78, 79, 80]),
    ("Consulta", 14, None, [], 16, 13198, [13199, 13200, 13201]),
    ("IQX", 6, None, [], 8, 2058, [2059, 2060, 2061]),
]

NOTAS = ("Columna A vacía en todo el archivo (posicional). Resumen: "
         "encabezado compuesto (grupos Medicina Familiar/"
         "Especialidades/Intervenciones quirúrgicas + años 2019-2025 "
         "y Meta 2025 en la fila sub) con Total Nacional en f16 "
         "(filas_total). Consulta e IQX: notas de Fuente/Nota al "
         "final declaradas en filas_nota.")


def main():
    catalogo = json.load(open(CATALOGO, encoding="utf-8"))
    fuente = next(f for f in catalogo["fuentes"] if f["id"] == ID)
    ver = fuente["verificaciones"][-1]
    hojas_leidas = {h["hoja"]: h["filas"]
                    for h in leer_filas(ver["ruta_local"],
                                        max_filas=200000)}
    perfil_hojas = []
    for nombre, fila_enc, fila_sub, filas_total, desde, hasta, \
            filas_nota in HOJAS:
        hoja = {"nombre": nombre, "tipo": "datos",
                "fila_encabezados": fila_enc,
                "columnas": hojas_leidas[nombre][fila_enc - 1],
                "filas_datos": {"desde": desde, "hasta": hasta}}
        if fila_sub:
            hoja["fila_encabezados_sub"] = fila_sub
        if filas_total:
            hoja["filas_total"] = filas_total
        if filas_nota:
            hoja["filas_nota"] = filas_nota
        perfil_hojas.append(hoja)
        print(f"  {nombre}: enc f{fila_enc}"
              + (f", sub f{fila_sub}" if fila_sub else "")
              + f", datos {desde}..{hasta}")
    perfil = {"id": ID, "huella_base": ver["huella"],
              "fecha": FECHA, "version_perfil": 1,
              "hojas": perfil_hojas, "notas": NOTAS}
    errores = validar(perfil)
    if errores:
        print("INVALIDO:", errores)
        return 1
    destino = ruta_perfil(CATALOGO, ID)
    guardar(destino, perfil)
    print("OK ->", destino, f"({len(perfil_hojas)} hojas)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
