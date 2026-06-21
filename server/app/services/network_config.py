"""Rilevamento e applicazione configurazione rete LAN (Raspberry Pi)."""

from __future__ import annotations

import ipaddress
import re
import socket
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _run(cmd: list[str], timeout: int = 8) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)


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


def nmcli_connection_mode() -> str:
    """Restituisce 'dhcp' o 'manual' se rilevabile, altrimenti ''."""
    con = _active_nmcli_connection()
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


def detect_lan() -> dict[str, str]:
    iface = default_interface()
    ip = primary_ip()
    gw = default_gateway()
    subnet = subnet_for_interface(iface) if iface else "255.255.255.0"
    mode = nmcli_connection_mode() or "dhcp"
    dns = gw or "8.8.8.8"
    return {
        "interface": iface,
        "ip": ip,
        "subnet": subnet,
        "gateway": gw,
        "dns": dns,
        "mode": mode,
    }


def validate_ipv4(value: str, *, allow_empty: bool = False) -> bool:
    if not value.strip():
        return allow_empty
    try:
        ipaddress.IPv4Address(value.strip())
        return True
    except ipaddress.AddressValueError:
        return False


def validate_manual_network(settings: dict[str, str]) -> str | None:
    if settings.get("NETWORK_MODE", "dhcp") != "manual":
        return None
    for key in ("LAN_IP", "LAN_SUBNET", "LAN_GATEWAY"):
        if not validate_ipv4(settings.get(key, "")):
            return f"Indirizzo non valido: {key}"
    if settings.get("LAN_DNS") and not validate_ipv4(settings["LAN_DNS"], allow_empty=True):
        return "DNS non valido"
    return None


def apply_lan_network(settings: dict[str, str]) -> tuple[bool, str]:
    script = ROOT / "standalone" / "apply-network.sh"
    if not script.is_file():
        return False, f"Script assente: {script}"

    mode = settings.get("NETWORK_MODE", "dhcp")
    args = [mode]
    if mode == "manual":
        args.extend([
            settings.get("LAN_IP", ""),
            settings.get("LAN_SUBNET", "255.255.255.0"),
            settings.get("LAN_GATEWAY", ""),
            settings.get("LAN_DNS", settings.get("LAN_GATEWAY", "")),
        ])

    for cmd in (["sudo", "-n", "bash", str(script), *args], ["bash", str(script), *args]):
        r = _run(cmd)
        if r.returncode == 0:
            msg = (r.stdout or r.stderr or "Rete aggiornata").strip()
            return True, msg

    hint = "sudo bash standalone/apply-network.sh " + " ".join(args)
    err = (r.stderr or r.stdout or "apply-network fallito").strip()
    return False, f"{err} — oppure: {hint}"
