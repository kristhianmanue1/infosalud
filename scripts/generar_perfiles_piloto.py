"""Genera los perfiles estructurales v1 de los archivos del piloto
CEPI (ADR-014, P11 ola 1). Lee las huellas del catálogo real, extrae
las columnas de la fila de encabezados declarada, valida contra el
contrato perfil-de-fuente v1 y escribe data/perfiles/<id>.json.
Uso: python3 scripts/generar_perfiles_piloto.py
"""
import json
import sys

from infosalud.estructura import leer_filas
from infosalud.perfiles import guardar, ruta_perfil, validar

FECHA = "2026-09-04"
CATALOGO = "data/fuentes.json"

# (id, [(hoja, fila_encabezados, datos_desde, datos_hasta,
#        clave_primaria, filas_total, tipo)])
PILoto = {
    "poblacion-pamf-siais-2025": [
        ("PAMF_202506_Consultorios", 8, 9, 17137, None, None, "datos"),
        ("PAMF_202506_UM_Totales", 8, 9, 1315,
         "Clave Presupuestal", None, "datos"),
        ("PAMF_202506_OOAD", 8, 10, 46, "Cve. OOAD", [9], "datos"),
        ("Unidades_No_Consideradas", 8, 9, 19,
         "Clave Presupuestal", None, "datos"),
    ],
    "poblacion-consultorios-medfam-pamf-2025": [
        ("Tot_Cons_MedFam", 8, 9, 1279,
         "Clave Presupuestal", None, "datos"),
        ("Tot_Cons_MF_OOAD", 8, 9, 46,
         "Clave Presupuestal", None, "datos"),
        ("PAMF_Consultorios", 7, 9, 17137, None, [8], "datos"),
        ("NO CONTEMPLADAS", 1, 2, 54,
         "CVE_PRESUPUESTAL", None, "datos"),
    ],
    "poblacion-usuaria-23n-simoc-unidad-2025": [
        ("Población_usuaria_2025_Esp", 11, 13, 317,
         "CVE_PRESUPUESTAL", [12], "datos"),
        ("Población_usuaria_2025_Urg", 11, 13, 287,
         "CVE_PRESUPUESTAL", [12], "datos"),
    ],
}

NOTAS = {
    "poblacion-pamf-siais-2025":
        "Subtotales por unidad embebidos (Consultorio=9999/"
        "Turno=99; 99999 en UM_Totales) dentro del rango de datos; "
        "conciliación pendiente (parser numérico, fase 3).",
    "poblacion-consultorios-medfam-pamf-2025":
        "PAMF_Consultorios trae subtotales 9999/99 por unidad "
        "embebidos; Tot_Cons_MF_OOAD es nivel OOAD (claves "
        "999999999999).",
    "poblacion-usuaria-23n-simoc-unidad-2025":
        "Fila 12 = total nacional por hoja (declarada en "
        "filas_total).",
}


def main():
    catalogo = json.load(open(CATALOGO, encoding="utf-8"))
    huellas = {}
    rutas = {}
    for fuente in catalogo["fuentes"]:
        if fuente["id"] in PILoto:
            ver = fuente["verificaciones"][-1]
            huellas[fuente["id"]] = ver["huella"]
            rutas[fuente["id"]] = ver["ruta_local"]

    fallos = 0
    for id_fuente, hojas_spec in PILoto.items():
        ruta = rutas[id_fuente]
        print(f"== {id_fuente} ({ruta})")
        hojas_leidas = leer_filas(ruta, max_filas=200000)
        indice = {h["hoja"]: h["filas"] for h in hojas_leidas}
        perfil_hojas = []
        for (nombre, fila_enc, desde, hasta, clave, filas_total,
             tipo) in hojas_spec:
            filas = indice[nombre]
            columnas = filas[fila_enc - 1]
            hoja = {"nombre": nombre, "tipo": tipo,
                    "fila_encabezados": fila_enc,
                    "columnas": columnas,
                    "filas_datos": {"desde": desde, "hasta": hasta}}
            if clave:
                hoja["clave_primaria"] = clave
                if clave not in columnas:
                    print(f"  AVISO: clave '{clave}' no está en "
                          f"columnas de {nombre}")
            if filas_total:
                hoja["filas_total"] = filas_total
            perfil_hojas.append(hoja)
        perfil = {"id": id_fuente, "huella_base": huellas[id_fuente],
                  "fecha": FECHA, "version_perfil": 1,
                  "hojas": perfil_hojas,
                  "notas": NOTAS.get(id_fuente, "")}
        errores = validar(perfil)
        if errores:
            print(f"  INVALIDO: {errores}")
            fallos += 1
            continue
        destino = ruta_perfil(CATALOGO, id_fuente)
        guardar(destino, perfil)
        print(f"  OK -> {destino} ({len(perfil_hojas)} hojas)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
