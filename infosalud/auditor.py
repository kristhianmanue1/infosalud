"""Auditoría de nivel 1: diff estructural por cambio de huella
(ADR-014 fase 4, §D del análisis de datos y auditoría).

Disparador: `vigencia-verificar` detecta huella nueva. Este módulo
compara la `estructura` observada de la última verificación contra
la previa (hojas nuevas/eliminadas, columnas agregadas/eliminadas)
y emite un informe versionado `data/auditorias/<id>/<fecha>.json`
con veredicto advisory: `conforme` o `requiere_revision`. El
veredicto jamás es `rechazada`: eso exige confirmación del
área/humano (corrección adversarial #3). El informe lleva la huella
de sí mismo (sha256 del contenido sin ese campo). Sólo stdlib.
"""

import hashlib
import json
from datetime import date, datetime
from pathlib import Path


class ErrorAuditoria(Exception):
    """Fallo con código HTTP asociado (contrato servicio v1)."""

    def __init__(self, codigo, mensaje):
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


def ruta_auditorias(ruta_catalogo, id_fuente):
    return (Path(ruta_catalogo).parent / "auditorias" / id_fuente)


def diff_estructura(anterior, nueva):
    """Diff de listas [{hoja, columnas}]. Devuelve hallazgos:
    lista de {tipo, hoja, detalle}."""
    an = {h["hoja"]: h.get("columnas") or [] for h in (anterior or [])}
    nu = {h["hoja"]: h.get("columnas") or [] for h in (nueva or [])}
    hallazgos = []
    for hoja in nu:
        if hoja not in an:
            hallazgos.append({"tipo": "hoja_nueva", "hoja": hoja,
                              "detalle": "hoja no existía antes"})
    for hoja in an:
        if hoja not in nu:
            hallazgos.append({"tipo": "hoja_eliminada", "hoja": hoja,
                              "detalle": "hoja ausente en la "
                                         "estructura nueva"})
    for hoja in nu:
        if hoja not in an:
            continue
        previas, actuales = an[hoja], nu[hoja]
        agregadas = [c for c in actuales if c and c not in previas]
        eliminadas = [c for c in previas if c and c not in actuales]
        if agregadas:
            hallazgos.append({
                "tipo": "columnas_agregadas", "hoja": hoja,
                "detalle": ", ".join(agregadas[:10])})
        if eliminadas:
            hallazgos.append({
                "tipo": "columnas_eliminadas", "hoja": hoja,
                "detalle": ", ".join(eliminadas[:10])})
    return hallazgos


def auditar(ruta_catalogo, id_fuente):
    """Ejecuta el nivel 1 sobre una fuente y escribe el informe.
    Devuelve el informe (dict). Falla con ErrorAuditoria si no hay
    al menos dos verificaciones con estructura (nada se infiere)."""
    from infosalud.catalogo import ErrorCatalogo, cargar_catalogo
    try:
        catalogo = cargar_catalogo(ruta_catalogo)
    except ErrorCatalogo as exc:
        raise ErrorAuditoria(500, str(exc)) from exc
    fuente = next((f for f in catalogo["fuentes"]
                   if f.get("id") == id_fuente), None)
    if fuente is None:
        raise ErrorAuditoria(404, f"id inexistente: '{id_fuente}'")
    con_estructura = [v for v in (fuente.get("verificaciones") or [])
                      if v.get("estructura")]
    if len(con_estructura) < 2:
        raise ErrorAuditoria(
            400, f"'{id_fuente}' tiene {len(con_estructura)} "
                 "verificación(es) con estructura; el diff estructural "
                 "exige al menos dos")
    previa, nueva = con_estructura[-2], con_estructura[-1]
    hallazgos = diff_estructura(previa.get("estructura"),
                                nueva.get("estructura"))
    informe = {
        "id": id_fuente,
        "contrato": "auditoria-nivel1-v1",
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "generador": "auditor-nivel-1 v1 (determinista, sin modelo)",
        "huella_anterior": previa.get("huella"),
        "huella_auditada": nueva.get("huella"),
        "fecha_verificacion_auditada": nueva.get("fecha"),
        "veredicto": "requiere_revision" if hallazgos else "conforme",
        "hallazgos": hallazgos,
    }
    cuerpo = json.dumps(informe, ensure_ascii=False,
                        sort_keys=True).encode("utf-8")
    informe["huella_informe"] = hashlib.sha256(cuerpo).hexdigest()
    destino = ruta_auditorias(ruta_catalogo, id_fuente)
    destino.mkdir(parents=True, exist_ok=True)
    nombre = f"{date.today().isoformat()}-{nueva.get('fecha')}.json"
    (destino / nombre).write_text(
        json.dumps(informe, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    return informe


def contar_requieren_revision(ruta_catalogo):
    """Visibilidad pasiva (P9): número de fuentes cuyo último
    informe de auditoría requiere revisión."""
    base = Path(ruta_catalogo).parent / "auditorias"
    if not base.is_dir():
        return 0
    total = 0
    for carpeta in sorted(base.iterdir()):
        informes = sorted(carpeta.glob("*.json"))
        if not informes:
            continue
        try:
            ultimo = json.loads(informes[-1].read_text(
                encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if ultimo.get("veredicto") == "requiere_revision":
            total += 1
    return total
