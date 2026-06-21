#!/bin/bash
# Applica rete Ethernet (LAN) o WiFi (WLAN) via NetworkManager
#
# Uso:
#   sudo bash standalone/apply-network.sh lan dhcp
#   sudo bash standalone/apply-network.sh lan manual IP MASK GW [DNS]
#   sudo TIMBRANFC_WLAN_PASSWORD='secret' bash standalone/apply-network.sh wlan dhcp "MySSID"
#   sudo TIMBRANFC_WLAN_PASSWORD='secret' bash standalone/apply-network.sh wlan manual "MySSID" IP MASK GW [DNS]
#
# Retrocompatibilità: apply-network.sh dhcp | manual ...

set -euo pipefail

CONN_LAN="TimbraNFC-LAN"
CONN_WLAN="TimbraNFC-WLAN"

if [ "$(id -u)" -ne 0 ]; then
    echo "Esegui con sudo"
    exit 1
fi

if ! command -v nmcli >/dev/null 2>&1; then
    echo "nmcli non trovato — installare NetworkManager"
    exit 1
fi

# Retrocompatibilità (solo LAN)
if [ "${1:-}" = "dhcp" ] || [ "${1:-}" = "manual" ]; then
    set -- lan "$@"
fi

LINK="${1:-lan}"
MODE="${2:-dhcp}"
shift 2 || true

SSID=""
IP=""
MASK="255.255.255.0"
GW=""
DNS=""

if [ "$LINK" = "wlan" ]; then
    SSID="${1:-}"
    shift || true
fi

if [ "$MODE" = "manual" ]; then
    IP="${1:-}"
    MASK="${2:-255.255.255.0}"
    GW="${3:-}"
    DNS="${4:-$GW}"
fi

WLAN_PASSWORD="${TIMBRANFC_WLAN_PASSWORD:-}"

_nm_device() {
    local kind="$1"
    nmcli -t -f DEVICE,TYPE device status 2>/dev/null \
        | awk -F: -v k="$kind" '$2 == k { print $1; exit }'
}

_prefix_len() {
    python3 - <<PY
import ipaddress
print(ipaddress.ip_network("0.0.0.0/${1}").prefixlen)
PY
}

_apply_ipv4() {
    local con="$1"
    local mode="$2"
    local addr="$3"
    local mask="$4"
    local gw="$5"
    local dns="$6"

    if [ "$mode" = "dhcp" ]; then
        nmcli connection modify "$con" \
            ipv4.method auto ipv4.addresses "" ipv4.gateway "" ipv4.dns ""
    elif [ "$mode" = "manual" ]; then
        if [ -z "$addr" ] || [ -z "$gw" ]; then
            echo "IP e gateway richiesti in modalità manual"
            exit 1
        fi
        local prefix
        prefix="$(_prefix_len "$mask")"
        nmcli connection modify "$con" \
            ipv4.method manual \
            ipv4.addresses "${addr}/${prefix}" \
            ipv4.gateway "$gw" \
            ipv4.dns "${dns:-$gw}"
    else
        echo "Modalità IP sconosciuta: $mode"
        exit 1
    fi
    nmcli connection up "$con"
}

_ensure_lan_connection() {
    local dev
    dev="$(_nm_device ethernet)"
    if [ -z "$dev" ]; then
        echo "Interfaccia Ethernet non trovata"
        exit 1
    fi
    if ! nmcli -t -f NAME connection show | grep -Fx "$CONN_LAN" >/dev/null 2>&1; then
        nmcli connection add type ethernet con-name "$CONN_LAN" ifname "$dev" autoconnect yes
    else
        nmcli connection modify "$CONN_LAN" connection.interface-name "$dev" connection.autoconnect yes
    fi
}

_ensure_wlan_connection() {
    local dev
    dev="$(_nm_device wifi)"
    if [ -z "$dev" ]; then
        echo "Interfaccia WiFi non trovata"
        exit 1
    fi
    if [ -z "$SSID" ]; then
        echo "SSID WiFi richiesto"
        exit 1
    fi
    if [ -z "$WLAN_PASSWORD" ]; then
        if nmcli -t -f NAME connection show | grep -Fx "$CONN_WLAN" >/dev/null 2>&1; then
            echo "Password WiFi non fornita — mantengo quella esistente su $CONN_WLAN"
        else
            echo "Password WiFi richiesta (TIMBRANFC_WLAN_PASSWORD)"
            exit 1
        fi
    fi

    if ! nmcli -t -f NAME connection show | grep -Fx "$CONN_WLAN" >/dev/null 2>&1; then
        if [ -z "$WLAN_PASSWORD" ]; then
            echo "Password WiFi richiesta per nuova connessione"
            exit 1
        fi
        nmcli connection add type wifi con-name "$CONN_WLAN" ifname "$dev" ssid "$SSID" \
            wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$WLAN_PASSWORD" \
            connection.autoconnect yes
    else
        nmcli connection modify "$CONN_WLAN" \
            connection.interface-name "$dev" \
            connection.autoconnect yes \
            802-11-wireless.ssid "$SSID"
        if [ -n "$WLAN_PASSWORD" ]; then
            nmcli connection modify "$CONN_WLAN" \
                wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$WLAN_PASSWORD"
        fi
    fi
}

if [ "$LINK" = "wlan" ]; then
    _ensure_wlan_connection
    nmcli connection modify "$CONN_LAN" connection.autoconnect no 2>/dev/null || true
    nmcli connection down "$CONN_LAN" 2>/dev/null || true
    if [ "$MODE" = "dhcp" ]; then
        _apply_ipv4 "$CONN_WLAN" dhcp "" "" "" ""
        echo "WiFi connesso a «${SSID}» (DHCP) su $CONN_WLAN"
    else
        _apply_ipv4 "$CONN_WLAN" manual "$IP" "$MASK" "$GW" "$DNS"
        echo "WiFi «${SSID}» IP statico ${IP} su $CONN_WLAN"
    fi
    exit 0
fi

if [ "$LINK" != "lan" ]; then
    echo "Tipo collegamento sconosciuto: $LINK (usa lan o wlan)"
    exit 1
fi

_ensure_lan_connection
nmcli connection modify "$CONN_WLAN" connection.autoconnect no 2>/dev/null || true
nmcli connection down "$CONN_WLAN" 2>/dev/null || true

if [ "$MODE" = "dhcp" ]; then
    _apply_ipv4 "$CONN_LAN" dhcp "" "" "" ""
    echo "Ethernet DHCP attivo su $CONN_LAN"
else
    _apply_ipv4 "$CONN_LAN" manual "$IP" "$MASK" "$GW" "$DNS"
    echo "Ethernet IP statico ${IP} su $CONN_LAN"
fi
