"""Perfil automático del derivado convertido de población usuaria 1N
(ADR-014, SPEC-11): una hoja por año (2004-2025); localiza la fila de
encabezado (celda que inicia con 'Clave') y declara datos desde la
primera fila con contenido posterior hasta la última con contenido.
Uso: PYTHONPATH=. python3 scripts/generar_perfil_usuaria_1n.py
"""
import json
import sys

from infosalud.estructura import leer_filas
from infosalud.perfiles import guardar, ruta_perfil, validar

ID = "poblacion-usuaria-1n-unidad-2004-2025-convertido"
CATALOGO = "data/fuentes.json"
FECHA = "2026-09-04"


def main():
    catalogo = json.load(open(CATALOGO, encoding="utf-8"))
    fuente = next(f for f in catalogo["fuentes"] if f["id"] == ID)
    ver = fuente["verificaciones"][-1]
    ruta = ver["ruta_local"]
    print("archivo:", ruta)
    hojas_leidas = leer_filas(ruta, max_filas=200000)
    perfil_hojas = []
    for hoja in hojas_leidas:
        filas = hoja["filas"]
        fila_enc = None
        for i, fila in enumerate(filas, start=1):
            if fila and isinstance(fila[0], str) and (
                    fila[0].startswith("Clave")
                    or fila[0].startswith("Cve.")):
                fila_enc = i
                break
        if fila_enc is None:
            print(f"  {hoja['hoja']}: sin encabezado, se omite")
            continue
        con = [i for i in range(fila_enc + 1, len(filas) + 1)
               if any(c.strip() for c in filas[i - 1])]
        if not con:
            print(f"  {hoja['hoja']}: sin datos tras encabezado")
            continue
        # Totales nacionales inmediatos tras el encabezado (fila con
        # celda 'TOTAL NACIONAL' dentro de las primeras filas con
        # contenido); las filas de datos reales tienen >= 3 celdas
        # con contenido (descarta espaciadoras de la conversión).
        window = con[:6]
        filas_total = [i for i in window
                       if any(c.strip().upper() == "TOTAL NACIONAL"
                              for c in filas[i - 1] if c)]
        datos = [i for i in con
                 if i not in filas_total
                 and sum(1 for c in filas[i - 1] if c.strip()) >= 3]
        if not datos:
            print(f"  {hoja['hoja']}: sin filas de datos reales")
            continue
        # Los totales nacionales preceden a los datos: el rango de
        # datos inicia tras el último total declarado (así queda
        # FUERA del rango, como exige el contrato ADR-014).
        desde = max([datos[0]] + [t + 1 for t in filas_total])
        hasta = datos[-1]
        perfil_hojas.append({
            "nombre": hoja["hoja"], "tipo": "datos",
            "fila_encabezados": fila_enc,
            "columnas": filas[fila_enc - 1],
            "filas_datos": {"desde": desde, "hasta": hasta},
            "clave_primaria": "Clave Presupuestal",
            **({"filas_total": filas_total} if filas_total else {}),
        })
        print(f"  {hoja['hoja']}: enc f{fila_enc}, "
              f"datos {desde}..{hasta}"
              + (f", totales {filas_total}" if filas_total else ""))
    perfil = {"id": ID, "huella_base": ver["huella"],
              "fecha": FECHA, "version_perfil": 1,
              "hojas": perfil_hojas,
              "notas": "Derivado de conversión LibreOffice (xls→"
                       "xlsx). Subtotales por unidad embebidos "
                       "(Consultorio=9999/Turno=99) y filas Total "
                       "Delegacional dentro del rango; conciliación "
                       "pendiente (fase 3)."}
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
