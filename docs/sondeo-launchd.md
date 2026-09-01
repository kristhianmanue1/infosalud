# Sondeo mensual con launchd (Mac mini)

Implementa la decisión 8 de `docs/adr/ADR-008`: sondeo automático
**mensual** de vigencias, más la verificación bajo demanda que ya
ofrece el CLI. Coherente con REQ-7 (intranet-first, Mac mini) y D6
(sólo lectura, frecuencia contenida, sin re-publicación).

## Qué hace

`scripts/sondeo.sh` ejecuta `vigencia-verificar` para todas las
fuentes del catálogo y appende el resultado a `data/sondeo.log`
(historial de sondeos con fecha y estado por fuente; los fallos
quedan registrados como `inaccesible` con causa — nunca éxito
inferido).

## Instalación (una vez, en la Mac mini)

1. Ajustar las rutas del usuario real en
   `docs/launchd/mx.imss.infosalud.sondeo.plist` (repositorio y
   rutas de log).
2. Copiar la plantilla al dominio del usuario:

   ```bash
   cp docs/launchd/mx.imss.infosalud.sondeo.plist \
      ~/Library/LaunchAgents/
   launchctl load ~/Library/LaunchAgents/mx.imss.infosalud.sondeo.plist
   ```

3. Verificar la próxima ejecución:

   ```bash
   launchctl list | grep infosalud
   launchctl start mx.imss.infosalud.sondeo   # prueba manual
   tail -20 data/sondeo.log
   ```

## Programación

Día 1 de cada mes a las 07:00 (`StartCalendarInterval` en la
plantilla). Frecuencia contenida según D6; cualquier cambio exige
revisar ADR-008.

## Desinstalar

```bash
launchctl unload ~/Library/LaunchAgents/mx.imss.infosalud.sondeo.plist
rm ~/Library/LaunchAgents/mx.imss.infosalud.sondeo.plist
```
