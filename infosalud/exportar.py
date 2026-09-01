"""Exportación de insumos a CSV y SQLite (ADR-011, SPEC-7).

Convierte el archivo local verificado de una fuente en productos
derivados conservando la evidencia de origen. Sólo lectura del
origen, sólo stdlib (csv, sqlite3), sin red. Topes declarados:
30 hojas, 200 columnas, 200 000 filas por hoja.
"""

import csv
import json
import os
import re
import shutil
import sqlite3
import tempfile

from infosalud.estructura import leer_filas

MAX_FILAS = 200_000
_TABLA = re.compile(r"[^0-9A-Za-z_]+")


def exportar(ruta_origen, destino, evidencia, formato_origen,
             formato_salida):
    """Escribe los productos derivados y devuelve las rutas creadas.

    evidencia: dict con id, huella y fecha de la verificación origen.
    destino no debe existir (sin pisar productos previos). Escribe a
    directorio temporal y mueve al final (sin productos parciales).
    """
    if formato_origen == "csv":
        hojas = _hojas_desde_csv(ruta_origen)
    else:
        hojas = leer_filas(ruta_origen, max_filas=MAX_FILAS)
    hojas = [h for h in hojas if h["filas"]]
    if not hojas:
        raise ValueError("el archivo no contiene filas exportables")
    if os.path.exists(destino):
        raise ValueError(f"el destino ya existe: {destino}")
    temporal = tempfile.mkdtemp(prefix=f"{evidencia['id']}__")
    try:
        if formato_salida == "csv":
            productos = _a_csv(hojas, evidencia, temporal, ruta_origen)
        else:
            productos = [_a_sqlite(hojas, evidencia, temporal,
                                   ruta_origen)]
        os.makedirs(os.path.dirname(os.path.abspath(destino)),
                    exist_ok=True)
        shutil.move(temporal, destino)
    except Exception:
        shutil.rmtree(temporal, ignore_errors=True)
        raise
    return [os.path.join(destino, p) for p in productos]


def _hojas_desde_csv(ruta):
    with open(ruta, encoding="utf-8-sig", newline="") as archivo:
        filas = [fila for fila in csv.reader(archivo)][:MAX_FILAS]
    return [{"hoja": "contenido", "filas": filas}]


def _evidencia(evidencia, ruta_origen, hojas):
    base = dict(evidencia)
    base["origen"] = os.path.abspath(ruta_origen)
    base["hojas"] = [h["hoja"] for h in hojas]
    return base


def _a_csv(hojas, evidencia, directorio, ruta_origen):
    id_fuente = evidencia["id"]
    productos = []
    for hoja in hojas:
        nombre = f"{id_fuente}__{_sanea(hoja['hoja'])}.csv"
        ruta = os.path.join(directorio, nombre)
        with open(ruta, "w", encoding="utf-8-sig",
                  newline="") as archivo:
            escritor = csv.writer(archivo)
            escritor.writerows(hoja["filas"])
        productos.append(nombre)
    ruta = os.path.join(directorio, f"{id_fuente}__evidencia.json")
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(_evidencia(evidencia, ruta_origen, hojas), archivo,
                  ensure_ascii=False, indent=2)
    productos.append(f"{id_fuente}__evidencia.json")
    return productos


def _a_sqlite(hojas, evidencia, directorio, ruta_origen):
    id_fuente = evidencia["id"]
    ruta = os.path.join(directorio, f"{id_fuente}.sqlite")
    usados = {"evidencia"}
    with sqlite3.connect(ruta) as conexion:
        conexion.execute(
            "CREATE TABLE evidencia (fuente TEXT, hoja TEXT, "
            "huella TEXT, fecha TEXT, filas INTEGER)")
        for hoja in hojas:
            tabla = _nombre_tabla(hoja["hoja"], usados)
            encabezados = [str(c) for c in hoja["filas"][0]]
            columnas = _columnas_unicas(encabezados)
            ancho = len(columnas)
            lista = ", ".join(f'"{c}" TEXT' for c in columnas)
            conexion.execute(f'CREATE TABLE "{tabla}" ({lista})')
            filas = []
            for fila in hoja["filas"][1:]:
                filas.append([str(fila[i]) if i < len(fila) else ""
                              for i in range(ancho)])
            if filas:
                insert = (f'INSERT INTO "{tabla}" VALUES '
                          f"({', '.join('?' * ancho)})")
                conexion.executemany(insert, filas)
            conexion.execute(
                "INSERT INTO evidencia VALUES (?, ?, ?, ?, ?)",
                (id_fuente, hoja["hoja"], evidencia.get("huella", ""),
                 evidencia.get("fecha", ""), len(filas)))
    return f"{id_fuente}.sqlite"


def _sanea(nombre):
    return (_TABLA.sub("_", nombre).strip("_") or "hoja")[:60]


def _nombre_tabla(nombre, usados):
    tabla = _sanea(nombre)
    candidato, sufijo = tabla, 2
    while candidato in usados:
        candidato = f"{tabla}_{sufijo}"
        sufijo += 1
    usados.add(candidato)
    return candidato


def _columnas_unicas(encabezados):
    usados, columnas = set(), []
    for posicion, encabezado in enumerate(encabezados):
        base = _TABLA.sub("_", encabezado).strip("_")[:60] \
            or f"col_{posicion + 1}"
        candidato, sufijo = base, 2
        while candidato in usados:
            candidato = f"{base}_{sufijo}"
            sufijo += 1
        usados.add(candidato)
        columnas.append(candidato)
    return columnas
