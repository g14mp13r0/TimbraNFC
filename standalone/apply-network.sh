#!/bin/bash
# Applica configurazione rete LAN (DHCP o statico) via NetworkManager
# Uso: sudo bash standalone/apply-network.sh dhcp
#      sudo bash standalone/apply-network.sh manual IP MASK GATEWAY [DNS]

set -euo pipefail

MODE="${1:-dhcp}"
IP="${2:-}"
MASK="${3:-255.255.255.0}"
GW="${4:-}"
DNS="${5:-$GW}"

if [ "$(id -u)" -ne 0 ]; then
    echo "Esegui con sudo"
    exit 1
fi

if ! command -v nmcli >/dev/null 2>&1; then
    echo "nmcli non trovato — installare NetworkManager"
    exit 1
fi

CON=$(nmcli -t -f NAME connection show --active 2>/dev/null | head -1 | cut -d: -f2-)
if [ -z "$CON" ]; then
    CON=$(nmcli -t -f NAME connection show 2>/dev/null | head -1 | cut -d: -f2-)
fi
if [ -z "$CON" ]; then
    echo "Nessuna connessione NetworkManager trovata"
    exit 1
fi

prefix=$(python3 - <<PY
import ipaddress
print(ipaddress.ip_network("0.0.0.0/${MASK}").prefixlen)
PY
)

if [ "$MODE" = "dhcp" ]; then
    nmcli connection modify "$CON" ipv4.method auto ipv4.addresses "" ipv4.gateway "" ipv4.dns ""
    nmcli connection up "$CON"
    echo "DHCP attivo su connessione: $CON"
    exit 0
fi

if [ "$MODE" != "manual" ]; then
    echo "Modalità sconosciuta: $MODE"
    exit 1
fi

if [ -z "$IP" ] || [ -z "$GW" ]; then
    echo "IP e gateway richiesti in modalità manual"
    exit 1
fi

nmcli connection modify "$CON" \
    ipv4.method manual \
    ipv4.addresses "${IP}/${prefix}" \
    ipv4.gateway "$GW" \
    ipv4.dns "${DNS:-$GW}"

nmcli connection up "$CON"
echo "IP statico ${IP}/${prefix} gw ${GW} su: $CON"
