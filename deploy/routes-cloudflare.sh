#!/bin/bash
# Rutas para que el túnel cloudflared salga por el WiFi (en1)
# aunque el cable de intranet (en0) esté conectado. Sólo afecta a
# los rangos edge de túneles de Cloudflare; el resto del tráfico
# sigue su curso normal.
# Uso (requiere sudo):  sudo routes-cloudflare.sh install|remove|status|daemon
set -u
ACCION=${1:-status}
GW=$(ipconfig getpacket en1 2>/dev/null | awk '/router \(ip/ {print $3}' | tr -d '{}')
GW=${GW:-192.168.100.1}
RANGES="198.41.192.0/24 198.41.200.0/24"
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_DST="/usr/local/sbin/routes-cloudflare.sh"
PLIST_SRC="$SRC_DIR/com.infosalud.routes-cloudflare.plist"
PLIST_DST="/Library/LaunchDaemons/com.infosalud.routes-cloudflare.plist"
aplicar() {
  for r in $RANGES; do
    route add -net "$r" "$GW" 2>/dev/null || route change -net "$r" "$GW" >/dev/null 2>&1
  done
}
case "$ACCION" in
  install)
    aplicar
    mkdir -p /usr/local/sbin
    cp "$0" "$SCRIPT_DST" && chmod 755 "$SCRIPT_DST"   # root-owned: sin ejecución de código editable por usuario
    sed -i '' "s|/Users/krisnova/www/infosalud/deploy/routes-cloudflare.sh|$SCRIPT_DST|" "$PLIST_SRC"
    cp "$PLIST_SRC" "$PLIST_DST"
    launchctl unload "$PLIST_DST" 2>/dev/null
    launchctl load "$PLIST_DST"
    echo "rutas instaladas vía $GW (en1) y daemon persistente cargado";;
  daemon)
    aplicar
    echo "rutas reaplicadas vía $GW (en1)";;
  remove)
    for r in $RANGES; do route delete -net "$r" "$GW" >/dev/null 2>&1; done
    launchctl unload "$PLIST_DST" 2>/dev/null
    echo "rutas eliminadas y daemon descargado";;
  status)
    for r in $RANGES; do route -n get "$r" 2>/dev/null | grep -E 'gateway|interface' | tr '\n' ' '; echo "← $r"; done;;
  *) echo "uso: $0 install|remove|status|daemon";;
esac
