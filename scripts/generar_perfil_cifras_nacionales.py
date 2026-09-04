"""Perfil de Cifras Nacionales 2025 (ADR-014, SPEC-11, enmienda
fila_encabezados_sub): 10 hojas; en cada una, fila de grupo
('Clave '), fila sub, filas de total (Nacional / Total
Delegaciones / Total OOAD) antes de los datos, y en algunas una
fila final '**' de nota que se excluye del rango.
Uso: PYTHONPATH=. python3 scripts/generar_perfil_cifras_nacionales.py
"""
import json
import sys

from infosalud.estructura import leer_filas
from infosalud.perfiles import guardar, ruta_perfil, validar

ID = "estadisticas-nacionales-cifras-2025"
CATALOGO = "data/fuentes.json"
FECHA = "2026-09-04"

# (hoja, fila_encabezados, fila_sub, filas_total, desde, hasta, notas)
HOJAS = [
    ("Consultas", 3, 4, [5, 6], 7, 67, [68]),
    ("Egresos", 4, 5, [7, 8], 9, 69, []),   # f6 es 3a fila de encabezado
    (" Aux Dx", 3, 4, [5, 6], 7, 67, []),
    ("Aux Tx", 3, 4, [5, 6], 7, 67, []),
    ("33 Procedimientos", 3, 4, [5, 6], 7, 67, []),
    ("Atenciones Prof. de Salud", 3, 4, [5, 6], 7, 67, [68]),
    ("Mortalidad", 3, 4, [5, 6], 7, 139, []),  # f138-139: fuera de IMSS
    ("PAMF Mes", 3, 4, [5], 6, 40, []),
    ("Banco de Sangre", 10, 11, [12, 13], 14, 74, []),
    ("Control", None, None, None, None, None, []),  # tipo otra
]

NOTAS = ("Encabezado compuesto: fila de grupo + fila sub "
         "(Egresos tiene una tercera fila de encabezado en f6, no "
         "expuesta). Filas de total (Nacional / Total Delegaciones "
         "/ Total OOAD) declaradas en filas_total, fuera del rango "
         "de datos. Fila final '**' de nota excluida del rango. "
         "columnas = fila de grupo tal como viene en el origen "
         "(celdas '' = celdas combinadas del grupo).")


def main():
    catalogo = json.load(open(CATALOGO, encoding="utf-8"))
    fuente = next(f for f in catalogo["fuentes"] if f["id"] == ID)
    ver = fuente["verificaciones"][-1]
    hojas_leidas = {h["hoja"]: h["filas"]
                    for h in leer_filas(ver["ruta_local"],
                                        max_filas=200000)}
    perfil_hojas = []
    for (nombre, fila_enc, fila_sub, filas_total, desde, hasta,
         filas_nota) in HOJAS:
        filas = hojas_leidas[nombre]
        if fila_enc is None:
            perfil_hojas.append({"nombre": nombre, "tipo": "otra"})
            print(f"  {nombre}: tipo otra")
            continue
        hoja = {"nombre": nombre, "tipo": "datos",
                "fila_encabezados": fila_enc,
                "fila_encabezados_sub": fila_sub,
                "columnas": filas[fila_enc - 1],
                "filas_datos": {"desde": desde, "hasta": hasta},
                "clave_primaria": "Clave ",
                "filas_total": filas_total}
        if filas_nota:
            hoja["filas_nota"] = filas_nota
        perfil_hojas.append(hoja)
        print(f"  {nombre}: enc f{fila_enc}, sub f{fila_sub}, "
              f"totales {filas_total}, datos {desde}..{hasta}")
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
