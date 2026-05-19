#!/usr/bin/env python3
"""
Hype HR — Paid Holiday Manager (Admin)
Developed by David | Nexuzy Lab

Features:
 - Add / Edit / Delete holidays in Firestore  (collection: holidays)
 - Bulk import from a list (seed data)
 - Month view — see all holidays in any given month
 - Each holiday document:
     date      : "YYYY-MM-DD"
     occasion  : "Diwali"  (display name)
     type      : "Festival" | "National" | "Optional" | "Restricted"
     paid      : true
 - Eligibility rule:
     Employee must have attendance marked AT LEAST 1 day in
     [date-2 days  …  date+2 days]  window to be counted as eligible.
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Optional

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except ImportError:
    print("[ERROR] firebase-admin not installed.")
    print("Run:  pip install firebase-admin")
    sys.exit(1)

try:
    import rich
    from rich.console import Console
    from rich.table import Table
    from rich.prompt import Prompt, Confirm
    from rich import print as rprint
except ImportError:
    print("[ERROR] rich not installed.")
    print("Run:  pip install rich")
    sys.exit(1)

console = Console()

# ─── Firebase init ──────────────────────────────────────────────────────────
SERVICE_ACCOUNT_PATH = os.path.join(os.path.dirname(__file__), "serviceAccountKey.json")

def init_firebase():
    if not firebase_admin._apps:
        if not os.path.exists(SERVICE_ACCOUNT_PATH):
            console.print(f"[red]serviceAccountKey.json not found at:[/red] {SERVICE_ACCOUNT_PATH}")
            console.print("Download it from Firebase Console → Project Settings → Service Accounts")
            sys.exit(1)
        cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
        firebase_admin.initialize_app(cred)
    return firestore.client()

# ─── Helpers ────────────────────────────────────────────────────────────────
HOLIDAY_TYPES = ["Festival", "National", "Optional", "Restricted"]

# ── SEED DATA ──────────────────────────────────────────────────────────────
# October 2026 pre-loaded holidays. Add more here before running bulk import.
SEED_HOLIDAYS = [
    {"date": "2026-10-02", "occasion": "Gandhi Jayanti",  "type": "National", "paid": True},
    {"date": "2026-10-20", "occasion": "Kali Puja",       "type": "Festival", "paid": True},
    {"date": "2026-10-22", "occasion": "Bhai Phonta",     "type": "Festival", "paid": True},
    {"date": "2026-10-24", "occasion": "Durga Puja",      "type": "Festival", "paid": True},
    {"date": "2026-10-31", "occasion": "Diwali",          "type": "Festival", "paid": True},
]

def parse_date(s: str) -> Optional[datetime]:
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    return None

def doc_id_from_date(date_str: str) -> str:
    return date_str.replace("-", "")

# ─── Holiday CRUD ────────────────────────────────────────────────────────────
def add_holiday(db):
    console.print("\n[bold cyan]=== Add / Update Holiday ===[/bold cyan]")

    date_input = Prompt.ask("Holiday date (YYYY-MM-DD or DD-MM-YYYY)")
    dt = parse_date(date_input)
    if not dt:
        console.print("[red]Invalid date format.[/red]")
        return
    date_str = dt.strftime("%Y-%m-%d")

    occasion = Prompt.ask("Occasion name", default="Holiday")

    console.print("Holiday types: " + ", ".join(f"[{i+1}] {t}" for i, t in enumerate(HOLIDAY_TYPES)))
    type_idx = Prompt.ask("Select type", choices=[str(i+1) for i in range(len(HOLIDAY_TYPES))], default="1")
    h_type = HOLIDAY_TYPES[int(type_idx) - 1]

    paid = Confirm.ask("Is this a paid holiday?", default=True)

    doc_id = doc_id_from_date(date_str)
    data = {
        "date": date_str,
        "occasion": occasion,
        "type": h_type,
        "paid": paid,
        "created_at": firestore.SERVER_TIMESTAMP,
    }

    db.collection("holidays").document(doc_id).set(data)
    console.print(f"[green]✅ Holiday saved:[/green] {date_str} — {occasion} ({h_type}, {'Paid' if paid else 'Unpaid'})")


def bulk_import_seed(db):
    """Import all SEED_HOLIDAYS into Firestore at once."""
    console.print(f"\n[bold cyan]=== Bulk Import Seed Holidays ===[/bold cyan]")
    console.print(f"[dim]Will import {len(SEED_HOLIDAYS)} holidays:[/dim]\n")

    # Preview table
    table = Table(show_lines=True)
    table.add_column("Date",     style="cyan")
    table.add_column("Occasion", style="bold")
    table.add_column("Type")
    table.add_column("Paid")
    for h in SEED_HOLIDAYS:
        table.add_row(h["date"], h["occasion"], h["type"], "✅ Yes" if h["paid"] else "❌ No")
    console.print(table)

    if not Confirm.ask("\nImport all these holidays?", default=True):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    batch = db.batch()
    for h in SEED_HOLIDAYS:
        doc_ref = db.collection("holidays").document(doc_id_from_date(h["date"]))
        batch.set(doc_ref, {**h, "created_at": firestore.SERVER_TIMESTAMP})
    batch.commit()
    console.print(f"[green]✅ {len(SEED_HOLIDAYS)} holidays imported successfully![/green]")


def list_holidays(db, show_table=True) -> list:
    docs = db.collection("holidays").order_by("date").stream()
    holidays = []
    for doc in docs:
        d = doc.to_dict()
        d["_id"] = doc.id
        holidays.append(d)

    if show_table:
        if not holidays:
            console.print("[yellow]No holidays found.[/yellow]")
            return holidays
        table = Table(title="All Holidays", show_lines=True)
        table.add_column("#",        style="dim", width=4)
        table.add_column("Date",     style="cyan")
        table.add_column("Day",      style="dim")
        table.add_column("Occasion", style="bold")
        table.add_column("Type")
        table.add_column("Paid")
        for i, h in enumerate(holidays, 1):
            dt = parse_date(h.get("date", ""))
            day_name = dt.strftime("%A") if dt else ""
            paid_icon = "✅ Yes" if h.get("paid") else "❌ No"
            table.add_row(str(i), h.get("date", ""), day_name, h.get("occasion", ""), h.get("type", ""), paid_icon)
        console.print(table)
    return holidays


def view_month_holidays(db):
    """Show all holidays in a specific month."""
    console.print("\n[bold cyan]=== View Holidays by Month ===[/bold cyan]")
    month_input = Prompt.ask("Enter month (YYYY-MM, e.g. 2026-10)", default="2026-10")
    try:
        datetime.strptime(month_input, "%Y-%m")
    except ValueError:
        console.print("[red]Invalid format. Use YYYY-MM[/red]")
        return

    docs = (
        db.collection("holidays")
        .where("date", ">=", f"{month_input}-01")
        .where("date", "<=", f"{month_input}-31")
        .order_by("date")
        .stream()
    )
    holidays = [doc.to_dict() for doc in docs]

    if not holidays:
        console.print(f"[yellow]No holidays found for {month_input}.[/yellow]")
        return

    # Month header
    dt_month = datetime.strptime(month_input, "%Y-%m")
    console.print(f"\n[bold magenta]📅 {dt_month.strftime('%B %Y')} — {len(holidays)} Holiday(s)[/bold magenta]\n")

    table = Table(show_lines=True)
    table.add_column("Date",     style="cyan", width=12)
    table.add_column("Day",      style="dim",  width=12)
    table.add_column("Occasion", style="bold")
    table.add_column("Type",     width=12)
    table.add_column("Paid",     width=10)
    for h in holidays:
        dt = parse_date(h.get("date", ""))
        day_name = dt.strftime("%A") if dt else ""
        paid_icon = "✅ Paid" if h.get("paid") else "❌ Unpaid"
        h_type = h.get("type", "")
        type_color = {
            "Festival": "yellow",
            "National": "green",
            "Optional": "blue",
            "Restricted": "red",
        }.get(h_type, "white")
        table.add_row(
            h.get("date", ""),
            day_name,
            h.get("occasion", ""),
            f"[{type_color}]{h_type}[/{type_color}]",
            paid_icon,
        )
    console.print(table)


def delete_holiday(db):
    holidays = list_holidays(db)
    if not holidays:
        return
    idx = Prompt.ask("Enter # to delete (or 0 to cancel)", default="0")
    if idx == "0":
        return
    try:
        h = holidays[int(idx) - 1]
    except (IndexError, ValueError):
        console.print("[red]Invalid selection.[/red]")
        return
    if Confirm.ask(f"Delete holiday [bold]{h['date']} — {h['occasion']}[/bold]?", default=False):
        db.collection("holidays").document(h["_id"]).delete()
        console.print("[green]Deleted.[/green]")


# ─── Eligibility check ───────────────────────────────────────────────────────
def check_eligibility(db):
    console.print("\n[bold cyan]=== Holiday Eligibility Check ===[/bold cyan]")
    holidays = list_holidays(db)
    if not holidays:
        return

    idx = Prompt.ask("Select holiday # to check eligibility", default="1")
    try:
        h = holidays[int(idx) - 1]
    except (IndexError, ValueError):
        console.print("[red]Invalid.[/red]")
        return

    h_date = datetime.strptime(h["date"], "%Y-%m-%d")
    window_dates = [
        (h_date + timedelta(days=d)).strftime("%Y-%m-%d")
        for d in range(-2, 3)
    ]
    console.print(f"Checking window: [cyan]{window_dates[0]}[/cyan] → [cyan]{window_dates[-1]}[/cyan]")

    employees_ref = db.collection("employees").stream()
    employees = {doc.id: doc.to_dict().get("name", doc.id) for doc in employees_ref}

    if not employees:
        console.print("[yellow]No employees found in Firestore.[/yellow]")
        return

    eligible   = []
    ineligible = []

    for emp_id, emp_name in employees.items():
        found = False
        for w_date in window_dates:
            month_key = w_date[:7]
            att_ref = (
                db.collection("attendance")
                .document(month_key)
                .collection(emp_id)
                .where("date", "==", w_date)
                .where("type", "in", ["IN", "COMPLETE"])
                .limit(1)
                .stream()
            )
            if any(True for _ in att_ref):
                found = True
                break
        (eligible if found else ineligible).append((emp_id, emp_name))

    table = Table(title=f"Eligibility — {h['occasion']} ({h['date']})", show_lines=True)
    table.add_column("Status",      width=14)
    table.add_column("Employee ID", style="dim")
    table.add_column("Name")
    for eid, ename in eligible:
        table.add_row("[green]✅ Eligible[/green]",     eid, ename)
    for eid, ename in ineligible:
        table.add_row("[red]❌ Not Eligible[/red]", eid, ename)
    console.print(table)
    console.print(f"\n[green]Eligible: {len(eligible)}[/green]   [red]Not Eligible: {len(ineligible)}[/red]")


# ─── Main menu ───────────────────────────────────────────────────────────────
def main():
    db = init_firebase()
    console.print("[bold magenta]\n🎉 Hype HR — Paid Holiday Manager[/bold magenta]")
    console.print("Developed by David | Nexuzy Lab\n")

    while True:
        console.print("[bold]--- Menu ---[/bold]")
        console.print(" [1] Add / Update Holiday (single)")
        console.print(" [2] Bulk Import Seed Holidays (Oct 2026 pre-loaded)")
        console.print(" [3] List All Holidays")
        console.print(" [4] View Holidays by Month")
        console.print(" [5] Delete Holiday")
        console.print(" [6] Check Eligibility for a Holiday")
        console.print(" [7] Exit")
        choice = Prompt.ask("Select", choices=["1","2","3","4","5","6","7"], default="3")

        if   choice == "1": add_holiday(db)
        elif choice == "2": bulk_import_seed(db)
        elif choice == "3": list_holidays(db)
        elif choice == "4": view_month_holidays(db)
        elif choice == "5": delete_holiday(db)
        elif choice == "6": check_eligibility(db)
        elif choice == "7":
            console.print("Bye!")
            break

if __name__ == "__main__":
    main()
