"""RetentionFlow terminal triage inbox.

A fast, keyboard-driven view of the generated retention emails — reads
serving.* directly from Postgres (no web layer), so it's instant.

    python tui.py            # interactive (arrows / j,k to move, q to quit)
    python tui.py --once     # render one frame and exit (smoke test)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

# Windows legacy consoles default to cp1252, which can't encode emoji/box glyphs
# or LLM-generated punctuation in the email bodies — force UTF-8 output.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from sqlalchemy import text  # noqa: E402

from backend.db.session import engine  # noqa: E402
from rich.console import Console, Group  # noqa: E402
from rich.layout import Layout  # noqa: E402
from rich.panel import Panel  # noqa: E402
from rich.table import Table  # noqa: E402
from rich.text import Text  # noqa: E402

PASS_BAR = 7.0  # judge pass threshold (1-10 scale)


# --- data ------------------------------------------------------------------

def load_rows() -> list[dict]:
    """The generated emails, newest model first, with grade + customer."""
    sql = text(
        """
        SELECT e.id            AS email_id,
               e.subject,
               e.body,
               e.prediction_id,
               p.customer_unique_id,
               p.churn_probability,
               s.overall_score,
               s.passed,
               s.reasoning,
               dn.display_name
          FROM serving.generated_emails e
          JOIN serving.predictions p ON p.id = e.prediction_id
          LEFT JOIN serving.eval_scores s ON s.email_id = e.id
          LEFT JOIN serving.customer_display_names dn
            ON dn.customer_unique_id = p.customer_unique_id
         ORDER BY p.churn_probability DESC
        """
    )
    drv = text(
        """
        SELECT prediction_id, feature_name, shap_value, rank
          FROM serving.shap_values
         WHERE prediction_id = ANY(:pids) AND rank <= 5
         ORDER BY prediction_id, rank
        """
    )
    with engine.connect() as c:
        rows = [dict(r) for r in c.execute(sql).mappings().all()]
        pids = [r["prediction_id"] for r in rows]
        by_pid: dict[int, list[dict]] = {}
        if pids:
            for d in c.execute(drv, {"pids": pids}).mappings():
                by_pid.setdefault(d["prediction_id"], []).append(dict(d))
    for r in rows:
        r["drivers"] = by_pid.get(r["prediction_id"], [])
    return rows


def _name(r: dict) -> str:
    return r["display_name"] or f"Customer {r['customer_unique_id'][:8].upper()}"


def _tier(p: float) -> tuple[str, str]:
    if p >= 0.85:
        return "CRIT", "bold red"
    if p >= 0.65:
        return "HIGH", "dark_orange"
    return "MED", "yellow"


# --- rendering -------------------------------------------------------------

def build(rows: list[dict], idx: int) -> Layout:
    # Left: the queue.
    tbl = Table(expand=True, box=None, padding=(0, 1))
    tbl.add_column("#", justify="right", style="grey50", width=3)
    tbl.add_column("Customer", ratio=2, no_wrap=True)
    tbl.add_column("Churn", justify="right", width=6)
    tbl.add_column("Judge", justify="right", width=7)
    for i, r in enumerate(rows):
        tier, color = _tier(float(r["churn_probability"]))
        score = r["overall_score"]
        judge = "—" if score is None else f"{float(score):.1f}"
        jstyle = "grey50" if score is None else ("green" if r["passed"] else "red")
        sel = i == idx
        prefix = "> " if sel else "  "
        row_style = "on grey23" if sel else ""
        tbl.add_row(
            f"{i + 1}",
            Text(prefix + _name(r), style=("bold " + color) if sel else color),
            f"{float(r['churn_probability']) * 100:.0f}%",
            Text(judge, style=jstyle),
            style=row_style,
        )
    left = Panel(tbl, title="[bold]Triage Inbox[/]", subtitle=f"{len(rows)} drafts",
                 border_style="grey50")

    # Right: the selected email + grade + drivers.
    r = rows[idx]
    tier, color = _tier(float(r["churn_probability"]))
    score = r["overall_score"]
    if score is None:
        verdict = Text("not graded", style="grey50")
    elif r["passed"]:
        verdict = Text(f"PASS  {float(score):.1f}/10 - clears the {PASS_BAR:.0f} bar", style="green")
    else:
        verdict = Text(f"HOLD  {float(score):.1f}/10 - below the {PASS_BAR:.0f} bar", style="red")

    head = Table.grid(expand=True)
    head.add_column(ratio=1)
    head.add_column(justify="right")
    head.add_row(
        Text(_name(r), style=f"bold {color}"),
        Text(f"{tier} · {float(r['churn_probability']) * 100:.0f}% churn", style=color),
    )

    drivers = Table(box=None, padding=(0, 1), expand=True)
    drivers.add_column("Top driver", style="grey70")
    drivers.add_column("SHAP", justify="right")
    for d in r["drivers"]:
        sv = float(d["shap_value"])
        drivers.add_row(d["feature_name"], Text(f"{sv:+.2f}", style="red" if sv > 0 else "green"))

    email = Group(
        Text(r["subject"], style="bold"),
        Text(""),
        Text(r["body"]),
    )
    right = Panel(
        Group(head, Text(""), verdict, Text(""),
              Panel(email, title="Email draft", border_style="grey37"),
              Panel(drivers, title="Why flagged (SHAP)", border_style="grey37")),
        title="[bold]Detail[/]", border_style="grey50",
    )

    root = Layout()
    root.split_column(
        Layout(Panel(Text(" RetentionFlow - terminal triage   |   up/down or j/k move   |   q quit",
                          style="grey70"), border_style="grey37"), size=3),
        Layout(name="body"),
    )
    root["body"].split_row(Layout(left, ratio=2), Layout(right, ratio=3))
    return root


# --- input loop ------------------------------------------------------------

def _read_key():
    """One keystroke (Windows msvcrt); returns 'up'/'down'/'quit'/None."""
    import msvcrt

    ch = msvcrt.getch()
    if ch in (b"\x00", b"\xe0"):  # arrow prefix
        ch2 = msvcrt.getch()
        return {b"H": "up", b"P": "down"}.get(ch2)
    return {b"q": "quit", b"k": "up", b"j": "down", b"\x03": "quit"}.get(ch.lower())


def main() -> None:
    console = Console()
    rows = load_rows()
    if not rows:
        console.print("[yellow]No generated emails yet — run the pipeline first.[/]")
        return

    if "--once" in sys.argv:
        console.print(build(rows, 0))
        return

    from rich.live import Live

    idx = 0
    with Live(build(rows, idx), console=console, screen=True, auto_refresh=False) as live:
        while True:
            key = _read_key()
            if key == "quit":
                break
            if key == "up":
                idx = (idx - 1) % len(rows)
            elif key == "down":
                idx = (idx + 1) % len(rows)
            else:
                continue
            live.update(build(rows, idx), refresh=True)


if __name__ == "__main__":
    main()
