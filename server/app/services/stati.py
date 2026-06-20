import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from shared.schemas import Azione, StatoDipendente
from shared.turni import calcola_ore_lavorate
from terminal.stati import azioni_valide, stato_da_timbrature


def stato_dipendente_oggi(azioni_oggi: list[Azione]) -> StatoDipendente:
    return stato_da_timbrature(azioni_oggi)


def azioni_valide_per_badge(azioni_oggi: list[Azione]) -> list[Azione]:
    stato = stato_da_timbrature(azioni_oggi)
    return azioni_valide(stato)
