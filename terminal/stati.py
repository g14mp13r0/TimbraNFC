"""Macchina a stati timbratura — modulo puro, senza I/O."""

from shared.schemas import Azione, StatoDipendente

# da_stato -> azione -> a_stato
TRANSIZIONI: dict[StatoDipendente, dict[Azione, StatoDipendente]] = {
    "FUORI_TURNO": {"IT": "IN_TURNO"},
    "IN_TURNO": {"IP": "IN_PAUSA", "FT": "FUORI_TURNO"},
    "IN_PAUSA": {"FP": "IN_TURNO"},
}

AZIONI_LABEL: dict[Azione, str] = {
    "IT": "Inizio Turno",
    "IP": "Inizio Pausa",
    "FP": "Fine Pausa",
    "FT": "Fine Turno",
}

STATO_DA_AZIONE: dict[Azione, StatoDipendente] = {
    "IT": "IN_TURNO",
    "IP": "IN_PAUSA",
    "FP": "IN_TURNO",
    "FT": "FUORI_TURNO",
}


def azioni_valide(stato: StatoDipendente) -> list[Azione]:
    return list(TRANSIZIONI.get(stato, {}).keys())


def azione_automatica(stato: StatoDipendente) -> Azione | None:
    """Timbratura NFC senza touch: FUORI_TURNO→IT, IN_TURNO→FT, IN_PAUSA→FT."""
    if stato == "FUORI_TURNO":
        return "IT"
    if stato in ("IN_TURNO", "IN_PAUSA"):
        return "FT"
    return None


def transizione_valida(stato: StatoDipendente, azione: Azione) -> bool:
    return azione in TRANSIZIONI.get(stato, {})


def nuovo_stato(stato: StatoDipendente, azione: Azione) -> StatoDipendente | None:
    return TRANSIZIONI.get(stato, {}).get(azione)


def stato_da_timbrature(azioni_oggi: list[Azione]) -> StatoDipendente:
    """Deriva lo stato corrente dall'ultima azione della giornata."""
    if not azioni_oggi:
        return "FUORI_TURNO"
    return STATO_DA_AZIONE.get(azioni_oggi[-1], "FUORI_TURNO")
