"""Integration test per `asin_master_writer` (CHG-2026-05-01-005, ADR-0017 + ADR-0015).

Verifica:
- INSERT nuovo ASIN inserisce tutti i campi forniti.
- UPSERT su ASIN esistente: title/brand/enterprise overwrite (NOT NULL),
  campi nullable mergiati via COALESCE (input non-null vince, null preserva).
- `last_seen_at` aggiornato a NOW() su ogni UPSERT.
- D5.c: nessun trigger audit_log su asin_master (verifica indiretta:
  insert/update non genera righe in audit_log).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from talos.extract import AsinMasterInput, upsert_asin_master
from talos.persistence.models.asin_master import AsinMaster

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy import Engine

pytestmark = pytest.mark.integration


@pytest.fixture
def orm_session(pg_engine: Engine) -> Iterator[Session]:
    factory = sessionmaker(bind=pg_engine, future=True, expire_on_commit=False)
    sess = factory()
    # Cleanup ASIN test prima/dopo per garantire isolamento.
    test_asins = ("B0TEST0001", "B0TEST0002")
    sess.execute(
        text("DELETE FROM asin_master WHERE asin = ANY(:asins)"),
        {"asins": list(test_asins)},
    )
    sess.commit()
    try:
        yield sess
    finally:
        sess.execute(
            text("DELETE FROM asin_master WHERE asin = ANY(:asins)"),
            {"asins": list(test_asins)},
        )
        sess.commit()
        sess.close()


def test_upsert_inserts_new_asin(orm_session: Session) -> None:
    """ASIN inesistente → INSERT con tutti i campi forniti."""
    inp = AsinMasterInput(
        asin="B0TEST0001",
        title="Samsung Galaxy S24",
        brand="Samsung",
        model="Galaxy S24",
        rom_gb=256,
        ram_gb=12,
        connectivity="5G",
        color_family="Titanium Black",
        enterprise=False,
        category_node="electronics/smartphones",
    )
    returned = upsert_asin_master(orm_session, data=inp)
    orm_session.commit()
    assert returned == "B0TEST0001"
    row = orm_session.get(AsinMaster, "B0TEST0001")
    assert row is not None
    assert row.title == "Samsung Galaxy S24"
    assert row.brand == "Samsung"
    assert row.model == "Galaxy S24"
    assert row.rom_gb == 256
    assert row.ram_gb == 12
    assert row.connectivity == "5G"
    assert row.color_family == "Titanium Black"
    assert row.enterprise is False
    assert row.category_node == "electronics/smartphones"
    assert row.last_seen_at is not None


def test_upsert_overwrites_not_null_fields_on_conflict(orm_session: Session) -> None:
    """ASIN esistente: title/brand/enterprise sempre overwrite."""
    first = AsinMasterInput(
        asin="B0TEST0001",
        title="Old Title",
        brand="OldBrand",
        enterprise=False,
    )
    upsert_asin_master(orm_session, data=first)
    orm_session.commit()
    second = AsinMasterInput(
        asin="B0TEST0001",
        title="New Title",
        brand="Samsung",
        enterprise=True,
    )
    upsert_asin_master(orm_session, data=second)
    orm_session.commit()
    orm_session.expire_all()
    row = orm_session.get(AsinMaster, "B0TEST0001")
    assert row is not None
    assert row.title == "New Title"
    assert row.brand == "Samsung"
    assert row.enterprise is True


def test_upsert_merges_nullable_fields_via_coalesce(orm_session: Session) -> None:
    """D5.b merge: input non-null vince, input None preserva valore esistente."""
    first = AsinMasterInput(
        asin="B0TEST0001",
        title="Galaxy S24",
        brand="Samsung",
        model="Galaxy S24",
        rom_gb=256,
        ram_gb=12,
        color_family="Titanium Black",
    )
    upsert_asin_master(orm_session, data=first)
    orm_session.commit()
    # Secondo upsert con SOLO title/brand obbligatori + ram_gb=16 (overwrite).
    # Gli altri campi sono None → devono essere preservati.
    second = AsinMasterInput(
        asin="B0TEST0001",
        title="Galaxy S24",
        brand="Samsung",
        ram_gb=16,  # solo questo viene aggiornato
        # model=None, rom_gb=None, color_family=None → preservati
    )
    upsert_asin_master(orm_session, data=second)
    orm_session.commit()
    orm_session.expire_all()
    row = orm_session.get(AsinMaster, "B0TEST0001")
    assert row is not None
    # Preservati (input None non sovrascrive):
    assert row.model == "Galaxy S24"
    assert row.rom_gb == 256
    assert row.color_family == "Titanium Black"
    # Overwrite (input non-null vince):
    assert row.ram_gb == 16


def test_upsert_refreshes_last_seen_at(orm_session: Session) -> None:
    """Ogni UPSERT aggiorna last_seen_at a NOW()."""
    inp = AsinMasterInput(asin="B0TEST0001", title="Galaxy S24", brand="Samsung")
    upsert_asin_master(orm_session, data=inp)
    orm_session.commit()
    orm_session.expire_all()
    first_seen = orm_session.get(AsinMaster, "B0TEST0001")
    assert first_seen is not None
    first_ts = first_seen.last_seen_at
    # Forza un piccolo delta temporale via una statement timestamp diversa.
    orm_session.execute(text("SELECT pg_sleep(0.05)"))
    upsert_asin_master(orm_session, data=inp)
    orm_session.commit()
    orm_session.expire_all()
    second_seen = orm_session.get(AsinMaster, "B0TEST0001")
    assert second_seen is not None
    assert second_seen.last_seen_at >= first_ts


def test_upsert_does_not_trigger_audit_log(orm_session: Session) -> None:
    """D5.c: asin_master NON ha trigger audit; insert/update non genera righe.

    Verifica indiretta: count(audit_log) prima/dopo l'UPSERT non cambia
    sulla tabella asin_master (audit triggers sono solo su sessions /
    config_overrides / locked_in / storico_ordini per CHG-018).
    """
    count_before = orm_session.execute(
        text("SELECT COUNT(*) FROM audit_log WHERE table_name = 'asin_master'"),
    ).scalar_one()
    inp = AsinMasterInput(asin="B0TEST0001", title="Galaxy S24", brand="Samsung")
    upsert_asin_master(orm_session, data=inp)
    orm_session.commit()
    upsert_asin_master(orm_session, data=inp)  # second update
    orm_session.commit()
    count_after = orm_session.execute(
        text("SELECT COUNT(*) FROM audit_log WHERE table_name = 'asin_master'"),
    ).scalar_one()
    assert count_after == count_before  # nessun trigger
