"""Populate ``serving.customer_display_names`` with deterministic, synthetic
Brazilian-style names for every customer in ``analytics.customer_features``.

The names are fictional and not derived from any real PII — they exist only
so the dashboard shows something friendlier than the 32-char hex hash. The
mapping is deterministic in the customer_unique_id, so the same customer
always renders with the same name across runs.

Usage:

    PYTHONPATH=src python -m backend.db.seed.display_names

Idempotent — re-running only inserts rows missing from the table.
"""

from __future__ import annotations

from sqlalchemy import text

from ..session import engine

FIRST_NAMES = (
    "Camila", "Diego", "Larissa", "Rafael", "Beatriz", "Thiago", "Mariana",
    "Bruno", "Aline", "Lucas", "Juliana", "Felipe", "Patricia", "Eduardo",
    "Fernanda", "Gabriel", "Carla", "Ricardo", "Sabrina", "André",
    "Vanessa", "Tiago", "Renata", "Marcelo", "Daniela", "Paulo", "Helena",
    "Rodrigo", "Luiza", "Murilo", "Tatiana", "Caio", "Bianca", "Henrique",
    "Letícia", "Vitor", "Amanda", "Pedro", "Isabela", "Gustavo", "Natália",
    "Leandro", "Carolina", "Matheus", "Priscila", "Vinícius", "Cristina",
    "Eric", "Débora", "João",
)

LAST_NAMES = (
    "Silva", "Santos", "Souza", "Oliveira", "Pereira", "Ferreira", "Lima",
    "Costa", "Carvalho", "Rodrigues", "Almeida", "Nascimento", "Lopes",
    "Gomes", "Ribeiro", "Martins", "Araújo", "Mendes", "Cavalcanti",
    "Moreira", "Fonseca", "Antunes", "Castro", "Nunes", "Pinto", "Barbosa",
    "Cardoso", "Rocha", "Vieira", "Teixeira", "Azevedo", "Correia",
    "Marques", "Freitas", "Ramos", "Bezerra", "Macedo", "Tavares", "Reis",
    "Monteiro",
)


def _display_name_for(customer_unique_id: str) -> str:
    """Deterministically pick a synthetic name from the customer's hex hash.

    Uses two non-overlapping byte windows so first / last vary independently —
    the same id always yields the same name across runs.
    """
    first = FIRST_NAMES[int(customer_unique_id[0:6], 16) % len(FIRST_NAMES)]
    last = LAST_NAMES[int(customer_unique_id[6:12], 16) % len(LAST_NAMES)]
    return f"{first} {last}"


def seed() -> dict:
    """Insert one display_name row per customer (skip rows already present).

    Returns ``{inserted, skipped, total}`` counts. Idempotent — only customers
    missing from ``serving.customer_display_names`` get a row.
    """
    with engine.connect() as conn:
        missing = conn.execute(
            text(
                """
                SELECT DISTINCT cf.customer_unique_id
                  FROM analytics.customer_features cf
                  LEFT JOIN serving.customer_display_names n
                    ON n.customer_unique_id = cf.customer_unique_id
                 WHERE n.customer_unique_id IS NULL
                """
            )
        ).scalars().all()

    if not missing:
        with engine.connect() as conn:
            total = conn.execute(
                text("SELECT COUNT(*) FROM serving.customer_display_names")
            ).scalar_one()
        return {"inserted": 0, "skipped": 0, "total": int(total)}

    rows = [
        {"cuid": cuid, "name": _display_name_for(cuid)} for cuid in missing
    ]
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO serving.customer_display_names (customer_unique_id, display_name)
                VALUES (:cuid, :name)
                ON CONFLICT (customer_unique_id) DO NOTHING
                """
            ),
            rows,
        )
        total = conn.execute(
            text("SELECT COUNT(*) FROM serving.customer_display_names")
        ).scalar_one()

    return {"inserted": len(rows), "skipped": 0, "total": int(total)}


if __name__ == "__main__":
    summary = seed()
    print(
        f"display_names: inserted {summary['inserted']:,} new, "
        f"{summary['total']:,} total rows"
    )
