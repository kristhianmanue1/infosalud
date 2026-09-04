"""Activa columnas_numericas en los perfiles de productividad
semanal 2025 (bump a v2): declara como numéricas las columnas cuyo
muestreo de datos sea >= 80% numérico (parser tolerante), excluida
la columna de nombres. En 'Resumen' las columnas se renombran a la
fila sub (años), que es la que nombra las métricas.
Uso: PYTHONPATH=. python3 scripts/activar_numericas_productividad.py
"""
import json
import sys

from infosalud.datos import _a_numero
from infosalud.estructura import leer_filas
from infosalud.perfiles import cargar, guardar, ruta_perfil, validar

ID = "seguimiento-productividad-semanal-2025"
CATALOGO = "data/fuentes.json"
FECHA = "2026-09-04"
NOMBRES_NO_NUMERICOS = {"OOAD/UMAE"}


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
        filas = hojas_leidas[hoja["nombre"]]
        rango = hoja["filas_datos"]
        datos = filas[rango["desde"] - 1:rango["hasta"]]
        # En hojas con encabezado compuesto, la fila sub es la que
        # nombra las métricas (años/Meta): usarla como columnas.
        if hoja.get("fila_encabezados_sub"):
            sub = hoja["fila_encabezados_sub"]
            hoja["columnas"] = filas[sub - 1]
        columnas = hoja["columnas"]
        numericas = []
        for i, columna in enumerate(columnas):
            if not columna.strip() \
                    or columna in NOMBRES_NO_NUMERICOS:
                continue
            valores = [fila[i] for fila in datos
                       if i < len(fila)]
            parseables = sum(1 for v in valores
                             if _a_numero(v) is not None)
            if valores and parseables / len(valores) >= 0.8:
                numericas.append(columna)
        if numericas:
            hoja["columnas_numericas"] = numericas
        print(f"  {hoja['nombre']}: {len(numericas)} columnas "
              f"numéricas de {len(columnas)}")
    perfil["notas"] = ("Columna A vacía (posicional). Resumen: "
                       "encabezado compuesto (grupos + años 2019-2025 "
                       "y Meta 2025 en fila sub, usada como "
                       "columnas) con Total Nacional en f16. "
                       "v2: columnas numéricas por muestreo "
                       "(>= 80% parseable); conciliación activa "
                       "contra las filas de total.")
    errores = validar(perfil)
    if errores:
        print("INVALIDO:", errores)
        return 1
    guardar(ruta, perfil)
    print("OK ->", ruta)
    return 0


if __name__ == "__main__":
    sys.exit(main())
