"""Perfiles por lote para los cortes CUUMSP (ADR-014, P11).

Todas las entregas mensuales comparten estructura: hoja 'Unidad
Médica' con encabezados en la fila 10 (col. 'CLUES  Salud') y datos
desde la 11. El lote declara esa hoja por archivo, marca como
'descriptiva' las hojas no tabulares conocidas y deja el resto sin
declarar (aparecen en hojas_sin_perfil). Valida cada perfil contra
el contrato y escribe data/perfiles/<id>.json.
Uso: PYTHONPATH=. python3 scripts/generar_perfiles_cuumsp_lote.py
"""
import json
import sys

from infosalud.estructura import leer_filas
from infosalud.perfiles import guardar, ruta_perfil, validar

CATALOGO = "data/fuentes.json"
FECHA = "2026-09-04"
FILA_ENCABEZADOS = 10
CLAVE = "CLUES  Salud"
HOJAS_DESCRIPTIVAS = {"Indice", "Diccionario", "Diccionari",
                      "Control de Cambios", "Histórico",
                      "Anexos COVID"}


def main():
    catalogo = json.load(open(CATALOGO, encoding="utf-8"))
    objetivos = [f for f in catalogo["fuentes"]
                 if f["id"].startswith("recursos-cuumsp-")
                 and f.get("formato") == "xlsx"]
    ok, fallos = 0, 0
    for fuente in objetivos:
        id_fuente = fuente["id"]
        verificaciones = [v for v in fuente.get("verificaciones", [])
                          if v.get("huella") and v.get("ruta_local")]
        if not verificaciones:
            print(f"{id_fuente}: sin archivo verificado, se omite")
            fallos += 1
            continue
        ver = verificaciones[-1]
        try:
            hojas_leidas = {h["hoja"]: h["filas"]
                            for h in leer_filas(ver["ruta_local"],
                                                max_filas=200000)}
        except Exception as exc:  # noqa: BLE001 (lote: reportar y seguir)
            print(f"{id_fuente}: ERROR de lectura: {exc}")
            fallos += 1
            continue
        um = hojas_leidas.get("Unidad Médica")
        if not um or len(um) < FILA_ENCABEZADOS:
            print(f"{id_fuente}: sin hoja 'Unidad Médica', se omite")
            fallos += 1
            continue
        columnas = um[FILA_ENCABEZADOS - 1]
        if CLAVE not in columnas:
            # Algunas entregas (2021) intercalan notas antes del
            # encabezado: localizar la fila con 'CLUES' en el
            # prefijo de la hoja.
            for i in range(FILA_ENCABEZADOS,
                           min(FILA_ENCABEZADOS + 10, len(um))):
                if CLAVE in um[i]:
                    fila_enc_local = i + 1
                    break
            else:
                print(f"{id_fuente}: '{CLAVE}' no en encabezados, "
                      "se omite")
                fallos += 1
                continue
            columnas = um[fila_enc_local - 1]
            fila_enc = fila_enc_local
        else:
            fila_enc = FILA_ENCABEZADOS
        con = [i for i in range(fila_enc + 1, len(um) + 1)
               if any(c.strip() for c in um[i - 1])]
        perfil_hojas = [{
            "nombre": "Unidad Médica", "tipo": "datos",
            "fila_encabezados": fila_enc,
            "columnas": columnas,
            "filas_datos": {"desde": con[0], "hasta": con[-1]},
            "clave_primaria": CLAVE,
        }]
        for nombre in hojas_leidas:
            if nombre == "Unidad Médica":
                continue
            if nombre in HOJAS_DESCRIPTIVAS:
                perfil_hojas.append({"nombre": nombre,
                                     "tipo": "descriptiva"})
        perfil = {"id": id_fuente, "huella_base": ver["huella"],
                  "fecha": FECHA, "version_perfil": 1,
                  "hojas": perfil_hojas,
                  "notas": "Perfil por lote (patrón común de la "
                           "entrega mensual). Sin filas de total "
                           "declaradas: verificación de totales "
                           "pendiente (fase 3). Hojas tabulares "
                           "secundarias aún sin declarar."}
        errores = validar(perfil)
        if errores:
            print(f"{id_fuente}: INVALIDO: {errores}")
            fallos += 1
            continue
        guardar(ruta_perfil(CATALOGO, id_fuente), perfil)
        ok += 1
        print(f"{id_fuente}: OK (datos {con[0]}..{con[-1]}, "
              f"{len(columnas)} columnas)")
    print(f"--- lote terminado: {ok} OK, {fallos} omitidos/fallidos")
    return 1 if fallos and not ok else 0


if __name__ == "__main__":
    sys.exit(main())
