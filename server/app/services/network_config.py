"""Rilevamento e applicazione configurazione rete LAN/WiFi (Raspberry Pi)."""

from __future__ import annotations

import ipaddress
import os
import re
import socket
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent

_LAN_CACHE: dict[str, str] | None = None
_LAN_CACHE_AT: float = 0.0
_LAN_CACHE_TTL = 30.0


def _run(cmd: list[str], timeout: int = 8, *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=env,
    )


def primary_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return ""


def default_gateway() -> str:
    out = _run(["ip", "route", "show", "default"]).stdout
    m = re.search(r"default via (\d+\.\d+\.\d+\.\d+)", out)
    return m.group(1) if m else ""


def default_interface() -> str:
    out = _run(["ip", "route", "show", "default"]).stdout
    m = re.search(r"dev (\S+)", out)
    return m.group(1) if m else ""


def interface_type(iface: str) -> str:
    if not iface:
        return ""
    out = _run(["nmcli", "-t", "-f", "TYPE", "device", "show", iface]).stdout.strip().lower()
    if "wifi" in out:
        return "wifi"
    if "ethernet" in out:
        return "ethernet"
    return out


def _prefix_to_mask(prefix: int) -> str:
    return str(ipaddress.IPv4Network(f"0.0.0.0/{prefix}").netmask)


def subnet_for_interface(iface: str) -> str:
    if not iface:
        return "255.255.255.0"
    out = _run(["ip", "-4", "addr", "show", "dev", iface]).stdout
    m = re.search(r"inet (\d+\.\d+\.\d+\.\d+)/(\d+)", out)
    if m:
        return _prefix_to_mask(int(m.group(2)))
    return "255.255.255.0"


def nmcli_connection_mode(con: str | None = None) -> str:
    """Restituisce 'dhcp' o 'manual' se rilevabile, altrimenti ''."""
    con = con or _active_nmcli_connection()
    if not con:
        return ""
    out = _run(["nmcli", "-g", "ipv4.method", "connection", "show", con]).stdout.strip().lower()
    if out in ("auto", "dhcp"):
        return "dhcp"
    if out == "manual":
        return "manual"
    return ""


def _active_nmcli_connection() -> str:
    out = _run(["nmcli", "-t", "-f", "NAME", "connection", "show", "--active"]).stdout.strip()
    if not out:
        return ""
    return out.splitlines()[0].split(":")[-1]


def detect_wifi_ssid(con: str | None = None) -> str:
    con = con or _active_nmcli_connection()
    if con:
        ssid = _run(["nmcli", "-g", "802-11-wireless.ssid", "connection", "show", con]).stdout.strip()
        if ssid and ssid != "--":
            return ssid
    out = _run(["nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi"]).stdout
    for line in out.splitlines():
        if line.startswith("yes:"):
            return line.split(":", 1)[1]
    return ""


def detect_link_type(iface: str | None = None) -> str:
    iface = iface or default_interface()
    if not iface:
        return "lan"
    if interface_type(iface) == "wifi":
        return "wlan"
    return "lan"


def detect_lan(*, force: bool = False) -> dict[str, str]:
    global _LAN_CACHE, _LAN_CACHE_AT
    now = time.monotonic()
    if not force and _LAN_CACHE is not None and (now - _LAN_CACHE_AT) < _LAN_CACHE_TTL:
        return dict(_LAN_CACHE)

    iface = default_interface()
    ip = primary_ip()
    gw = default_gateway()
    subnet = subnet_for_interface(iface) if iface else "255.255.255.0"
    con = _active_nmcli_connection()
    mode = nmcli_connection_mode(con) or "dhcp"
    link = detect_link_type(iface)
    ssid = detect_wifi_ssid(con) if link == "wlan" else ""
    dns = gw or "8.8.8.8"
    _LAN_CACHE = {
        "interface": iface,
        "ip": ip,
        "subnet": subnet,
        "gateway": gw,
        "dns": dns,
        "mode": mode,
        "link": link,
        "ssid": ssid,
    }
    _LAN_CACHE_AT = now
    return dict(_LAN_CACHE)


def validate_ipv4(value: str, *, allow_empty: bool = False) -> bool:
    if not value.strip():
        return allow_empty
    try:
        ipaddress.IPv4Address(value.strip())
        return True
    except ipaddress.AddressValueError:
        return False


def validate_network_settings(settings: dict[str, str], env: dict[str, str] | None = None) -> str | None:
    env = env or {}
    if settings.get("NETWORK_MODE", "dhcp") == "manual":
        for key in ("LAN_IP", "LAN_SUBNET", "LAN_GATEWAY"):
            if not validate_ipv4(settings.get(key, "")):
                return f"Indirizzo non valido: {key}"
        if settings.get("LAN_DNS") and not validate_ipv4(settings["LAN_DNS"], allow_empty=True):
            return "DNS non valido"

    if settings.get("NETWORK_LINK", "lan") == "wlan":
        if not settings.get("WLAN_SSID", "").strip():
            return "SSID WiFi richiesto"
        pwd = settings.get("WLAN_PASSWORD", "").strip() or env.get("WLAN_PASSWORD", "").strip()
        ssid_changed = settings.get("WLAN_SSID", "").strip() != env.get("WLAN_SSID", "").strip()
        if not pwd and (ssid_changed or not env.get("WLAN_PASSWORD")):
            return "Password WiFi richiesta"
    return None


def validate_manual_network(settings: dict[str, str]) -> str | None:
    return validate_network_settings(settings)


def apply_lan_network(settings: dict[str, str], env: dict[str, str] | None = None) -> tuple[bool, str]:
    from server.app.services.settings_env import parse_env_file

    env = env or parse_env_file()
    script = ROOT / "standalone" / "apply-network.sh"
    if not script.is_file():
        return False, f"Script assente: {script}"

    link = settings.get("NETWORK_LINK", "lan")
    mode = settings.get("NETWORK_MODE", "dhcp")
    ssid = settings.get("WLAN_SSID", "")

    args = [link, mode]
    if link == "wlan":
        args.append(ssid)
    if mode == "manual":
        args.extend([
            settings.get("LAN_IP", ""),
            settings.get("LAN_SUBNET", "255.255.255.0"),
            settings.get("LAN_GATEWAY", ""),
            settings.get("LAN_DNS", settings.get("LAN_GATEWAY", "")),
        ])

    wlan_pwd = settings.get("WLAN_PASSWORD", "").strip() or env.get("WLAN_PASSWORD", "").strip()
    run_env = os.environ.copy()
    if wlan_pwd:
        run_env["TIMBRANFC_WLAN_PASSWORD"] = wlan_pwd

    r: subprocess.CompletedProcess[str] | None = None
    for cmd in (["sudo", "-n", "bash", str(script), *args], ["bash", str(script), *args]):
        r = _run(cmd, timeout=45, env=run_env)
        if r.returncode == 0:
            msg = (r.stdout or r.stderr or "Rete aggiornata").strip()
            global _LAN_CACHE, _LAN_CACHE_AT
            _LAN_CACHE = None
            _LAN_CACHE_AT = 0.0
            return True, msg

    hint = "sudo TIMBRANFC_WLAN_PASSWORD='...' bash standalone/apply-network.sh " + " ".join(
        f'"{a}"' if " " in str(a) else str(a) for a in args
    )
    err = (r.stderr or r.stdout or "apply-network fallito").strip() if r else "apply-network fallito"
    return False, f"{err} — oppure: {hint}"
