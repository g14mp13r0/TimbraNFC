from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.app.db import Base


class Sede(Base):
    __tablename__ = "sedi"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    indirizzo: Mapped[str | None] = mapped_column(String(255))
    creato_il: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    dipendenti: Mapped[list["Dipendente"]] = relationship(back_populates="sede")
    dispositivi: Mapped[list["Dispositivo"]] = relationship(back_populates="sede")


class Dipendente(Base):
    __tablename__ = "dipendenti"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sede_id: Mapped[int] = mapped_column(ForeignKey("sedi.id"), nullable=False)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    cognome: Mapped[str] = mapped_column(String(100), nullable=False)
    badge_uid: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    reparto: Mapped[str | None] = mapped_column(String(100))
    attivo: Mapped[bool] = mapped_column(Boolean, default=True)
    creato_il: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    sede: Mapped["Sede"] = relationship(back_populates="dipendenti")
    timbrature: Mapped[list["Timbratura"]] = relationship(back_populates="dipendente")


class Dispositivo(Base):
    __tablename__ = "dispositivi"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sede_id: Mapped[int] = mapped_column(ForeignKey("sedi.id"), nullable=False)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    device_uuid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    versione_sw: Mapped[str | None] = mapped_column(String(20))
    ultimo_heartbeat: Mapped[datetime | None] = mapped_column(DateTime)
    stato: Mapped[str] = mapped_column(String(20), default="offline")
    ip_locale: Mapped[str | None] = mapped_column(String(45))
    creato_il: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    sede: Mapped["Sede"] = relationship(back_populates="dispositivi")
    timbrature: Mapped[list["Timbratura"]] = relationship(back_populates="dispositivo")
    comandi: Mapped[list["DeviceComando"]] = relationship(back_populates="dispositivo")


class Timbratura(Base):
    __tablename__ = "timbrature"
    __table_args__ = (UniqueConstraint("dispositivo_id", "id_locale_origine", name="uq_dedup"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dipendente_id: Mapped[int] = mapped_column(ForeignKey("dipendenti.id"), nullable=False)
    dispositivo_id: Mapped[int] = mapped_column(ForeignKey("dispositivi.id"), nullable=False)
    azione: Mapped[str] = mapped_column(String(2), nullable=False)
    timestamp_terminale: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ricevuto_il: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    id_locale_origine: Mapped[int | None] = mapped_column(Integer)

    dipendente: Mapped["Dipendente"] = relationship(back_populates="timbrature")
    dispositivo: Mapped["Dispositivo"] = relationship(back_populates="timbrature")


class DeviceLog(Base):
    __tablename__ = "device_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dispositivo_id: Mapped[int] = mapped_column(ForeignKey("dispositivi.id"), nullable=False)
    livello: Mapped[str] = mapped_column(String(10), nullable=False)
    messaggio: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class UtenteAdmin(Base):
    __tablename__ = "utenti_admin"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    ruolo: Mapped[str] = mapped_column(String(20), default="admin")
    creato_il: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class DeviceComando(Base):
    __tablename__ = "device_comandi"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dispositivo_id: Mapped[int] = mapped_column(ForeignKey("dispositivi.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    payload: Mapped[str | None] = mapped_column(Text)
    eseguito: Mapped[bool] = mapped_column(Boolean, default=False)
    creato_il: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    dispositivo: Mapped["Dispositivo"] = relationship(back_populates="comandi")
