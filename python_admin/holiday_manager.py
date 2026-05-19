#!/usr/bin/env python3
"""
Hype HR — Paid Holiday Manager (Admin)
Developed by David | Nexuzy Lab

Features:
 - Add / Edit / Delete holidays in Firestore  (collection: holidays)
 - Each holiday document:
     date      : "YYYY-MM-DD"
     occasion  : "Diwali"  (display name)
     type      : "Festival" | "National" | "Optional" | "Restricted"
     paid      : true
 - Eligibility rule:
     Employee must have attendance marked AT LEAST 1 day in
     [date-2 days  …  date+2 days]  window to be counted as eligible.
 - View upcoming holidays
 - View which employees are eligible for a specific holiday
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

def parse_date(s: str) -> Optional[datetime]:
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    return None

def doc_id_from_date(date_str: str) -> str:
    """Use YYYY-MM-DD as Firestore document ID for easy querying."""
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
        table = Table(title="Holidays", show_lines=True)
        table.add_column("#", style="dim", width=4)
        table.add_column("Date", style="cyan")
        table.add_column("Occasion", style="bold")
        table.add_column("Type")
        table.add_column("Paid")
        for i, h in enumerate(holidays, 1):
            paid_icon = "✅ Yes" if h.get("paid") else "❌ No"
            table.add_row(str(i), h.get("date", ""), h.get("occasion", ""), h.get("type", ""), paid_icon)
        console.print(table)
    return holidays

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
    """
    For a chosen holiday, list all employees who have attendance within
    [holiday_date - 2 days ... holiday_date + 2 days].
    Attendance documents live at:  attendance/{YYYY-MM}/{employee_id}/{records}
    We check the simplified daily doc path used by the app.
    """
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
        for d in range(-2, 3)  # -2, -1, 0, +1, +2
    ]
    console.print(f"Checking attendance window: {window_dates[0]} to {window_dates[-1]}")

    # Collect all employee IDs from attendance collection
    employees_ref = db.collection("employees").stream()
    employees = {doc.id: doc.to_dict().get("name", doc.id) for doc in employees_ref}

    if not employees:
        console.print("[yellow]No employees found in Firestore.[/yellow]")
        return

    eligible = []
    ineligible = []

    for emp_id, emp_name in employees.items():
        found = False
        for w_date in window_dates:
            month_key = w_date[:7]  # YYYY-MM
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
        if found:
            eligible.append((emp_id, emp_name))
        else:
            ineligible.append((emp_id, emp_name))

    table = Table(title=f"Eligibility for {h['occasion']} ({h['date']})", show_lines=True)
    table.add_column("Status", width=12)
    table.add_column("Employee ID")
    table.add_column("Name")

    for eid, ename in eligible:
        table.add_row("✅ Eligible", eid, ename)
    for eid, ename in ineligible:
        table.add_row("❌ Not Eligible", eid, ename)

    console.print(table)
    console.print(f"\n[green]Eligible: {len(eligible)}[/green]  [red]Not Eligible: {len(ineligible)}[/red]")

# ─── Main menu ───────────────────────────────────────────────────────────────
def main():
    db = init_firebase()
    console.print("[bold magenta]\n🎉 Hype HR — Paid Holiday Manager[/bold magenta]")
    console.print("Developed by David | Nexuzy Lab\n")

    while True:
        console.print("[bold]--- Menu ---[/bold]")
        console.print(" [1] Add / Update Holiday")
        console.print(" [2] List All Holidays")
        console.print(" [3] Delete Holiday")
        console.print(" [4] Check Eligibility for a Holiday")
        console.print(" [5] Exit")
        choice = Prompt.ask("Select", choices=["1","2","3","4","5"], default="2")

        if choice == "1":
            add_holiday(db)
        elif choice == "2":
            list_holidays(db)
        elif choice == "3":
            delete_holiday(db)
        elif choice == "4":
            check_eligibility(db)
        elif choice == "5":
            console.print("Bye!")
            break

if __name__ == "__main__":
    main()
