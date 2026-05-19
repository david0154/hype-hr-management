"""
Hype HR — Paid Holiday Manager Module (Tkinter GUI)
Developed by David | Nexuzy Lab

Part of admin_app. Registered as '🎉 Holidays' tab in main.py.

Features:
  - Add single holiday (date picker + form)
  - Bulk import preset seed list (Oct 2026 pre-loaded)
  - List / view all holidays with coloured type badges
  - View by month filter
  - Delete holiday
  - Eligibility check — employees with attendance ±2 days get paid holiday

Firestore structure:
  holidays/{YYYYMMDD}/
    date      : "YYYY-MM-DD"
    occasion  : "Diwali"
    type      : "Festival" | "National" | "Optional" | "Restricted"
    paid      : true
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, timedelta
from utils.firebase_client import get_firestore_client

# ── Seed data (Oct 2026) ────────────────────────────────────────────────────
SEED_HOLIDAYS = [
    {"date": "2026-10-02", "occasion": "Gandhi Jayanti", "type": "National", "paid": True},
    {"date": "2026-10-20", "occasion": "Kali Puja",      "type": "Festival", "paid": True},
    {"date": "2026-10-22", "occasion": "Bhai Phonta",    "type": "Festival", "paid": True},
    {"date": "2026-10-24", "occasion": "Durga Puja",     "type": "Festival", "paid": True},
    {"date": "2026-10-31", "occasion": "Diwali",         "type": "Festival", "paid": True},
]

TYPE_COLORS = {
    "Festival":   "#f77f00",
    "National":   "#27ae60",
    "Optional":   "#2980b9",
    "Restricted": "#c0392b",
}

HOLIDAY_TYPES = ["Festival", "National", "Optional", "Restricted"]


def doc_id(date_str: str) -> str:
    return date_str.replace("-", "")


def parse_date(s: str):
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    return None


# ══════════════════════════════════════════════════════════════════════════════
class HolidayModule:
    """Main Tkinter panel — called by main.py as HolidayModule(frame, user)."""

    BG       = "#0d1b2a"
    CARD_BG  = "#1a2740"
    FG       = "#f0f0f0"
    ACCENT   = "#f77f00"
    BTN_FG   = "#ffffff"
    ENTRY_BG = "#0d2137"
    SEL_BG   = "#1e3a5f"

    def __init__(self, parent, current_user=None):
        self.parent = parent
        self.user   = current_user or {}
        self.db     = get_firestore_client()
        self._build_ui()
        self._load_holidays()

    # ── UI construction ──────────────────────────────────────────────────────
    def _build_ui(self):
        self.parent.configure(bg=self.BG)

        # Top toolbar
        toolbar = tk.Frame(self.parent, bg=self.CARD_BG, pady=8)
        toolbar.pack(fill="x", padx=10, pady=(10, 0))

        tk.Label(toolbar, text="🎉 Paid Holiday Manager",
                 font=("Arial", 14, "bold"), bg=self.CARD_BG,
                 fg=self.ACCENT).pack(side="left", padx=12)

        # Buttons right-side
        for txt, cmd in [
            ("➕ Add Holiday",          self._open_add_dialog),
            ("📥 Bulk Import (Oct 2026)", self._bulk_import),
            ("🔍 Filter by Month",       self._filter_month),
            ("🗑 Delete Selected",       self._delete_selected),
            ("👥 Check Eligibility",     self._check_eligibility),
            ("🔄 Refresh",              self._load_holidays),
        ]:
            tk.Button(
                toolbar, text=txt, command=cmd,
                bg=self.ACCENT, fg=self.BTN_FG,
                font=("Arial", 9, "bold"), relief="flat",
                padx=10, pady=4, cursor="hand2"
            ).pack(side="right", padx=4)

        # Treeview
        tree_frame = tk.Frame(self.parent, bg=self.BG)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        cols = ("date", "day", "occasion", "type", "paid")
        self.tree = ttk.Treeview(tree_frame, columns=cols,
                                 show="headings", selectmode="browse")

        style = ttk.Style()
        style.configure("Treeview",
                        background=self.CARD_BG,
                        foreground=self.FG,
                        fieldbackground=self.CARD_BG,
                        rowheight=30,
                        font=("Arial", 10))
        style.configure("Treeview.Heading",
                        background=self.ACCENT,
                        foreground="white",
                        font=("Arial", 10, "bold"))
        style.map("Treeview", background=[("selected", self.SEL_BG)])

        headers = {
            "date":    ("Date",     120),
            "day":     ("Day",      100),
            "occasion":("Occasion", 200),
            "type":    ("Type",     110),
            "paid":    ("Paid",      80),
        }
        for col, (head, w) in headers.items():
            self.tree.heading(col, text=head)
            self.tree.column(col, width=w, anchor="center")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",
                            command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        # Status bar
        self.status_var = tk.StringVar(value="Loading holidays...")
        tk.Label(self.parent, textvariable=self.status_var,
                 bg=self.BG, fg="#888",
                 font=("Arial", 9)).pack(anchor="w", padx=12, pady=(0, 6))

    # ── Data load ────────────────────────────────────────────────────────────
    def _load_holidays(self, month_filter=None):
        self.tree.delete(*self.tree.get_children())
        try:
            q = self.db.collection("holidays").order_by("date")
            if month_filter:
                q = (q.where("date", ">=", f"{month_filter}-01")
                      .where("date", "<=", f"{month_filter}-31"))
            docs = q.stream()
            count = 0
            for doc in docs:
                h = doc.to_dict()
                h["_id"] = doc.id
                dt = parse_date(h.get("date", ""))
                day_name = dt.strftime("%A") if dt else ""
                paid_txt = "✅ Yes" if h.get("paid") else "❌ No"
                h_type   = h.get("type", "")
                tag      = h_type.lower()
                self.tree.insert("", "end",
                    iid=doc.id,
                    values=(h["date"], day_name, h.get("occasion", ""),
                            h_type, paid_txt),
                    tags=(tag,))
                color = TYPE_COLORS.get(h_type, self.FG)
                self.tree.tag_configure(tag, foreground=color)
                count += 1
            label = f"month {month_filter}" if month_filter else "all months"
            self.status_var.set(f"✅ {count} holiday(s) loaded — {label}")
        except Exception as e:
            self.status_var.set(f"❌ Error: {e}")

    # ── Add dialog ───────────────────────────────────────────────────────────
    def _open_add_dialog(self):
        dlg = tk.Toplevel(self.parent)
        dlg.title("Add / Update Holiday")
        dlg.geometry("420x340")
        dlg.configure(bg=self.CARD_BG)
        dlg.grab_set()

        fields = {}

        def row(label, widget_fn, default=""):
            r = tk.Frame(dlg, bg=self.CARD_BG)
            r.pack(fill="x", padx=20, pady=6)
            tk.Label(r, text=label, bg=self.CARD_BG, fg=self.FG,
                     font=("Arial", 10), width=14, anchor="w").pack(side="left")
            w = widget_fn(r)
            w.pack(side="left", fill="x", expand=True)
            if hasattr(w, "insert") and default:
                w.insert(0, default)
            return w

        def entry(parent):
            e = tk.Entry(parent, bg=self.ENTRY_BG, fg=self.FG,
                         insertbackground=self.FG, relief="flat",
                         font=("Arial", 10))
            return e

        fields["date"]    = row("Date (YYYY-MM-DD)", entry,
                                datetime.today().strftime("%Y-%m-%d"))
        fields["occasion"]= row("Occasion", entry, "Holiday")

        # Type dropdown
        type_var = tk.StringVar(value="Festival")
        r2 = tk.Frame(dlg, bg=self.CARD_BG)
        r2.pack(fill="x", padx=20, pady=6)
        tk.Label(r2, text="Type", bg=self.CARD_BG, fg=self.FG,
                 font=("Arial", 10), width=14, anchor="w").pack(side="left")
        ttk.Combobox(r2, textvariable=type_var,
                     values=HOLIDAY_TYPES,
                     state="readonly", width=20).pack(side="left")

        # Paid checkbox
        paid_var = tk.BooleanVar(value=True)
        r3 = tk.Frame(dlg, bg=self.CARD_BG)
        r3.pack(fill="x", padx=20, pady=6)
        tk.Label(r3, text="Paid Holiday", bg=self.CARD_BG, fg=self.FG,
                 font=("Arial", 10), width=14, anchor="w").pack(side="left")
        tk.Checkbutton(r3, variable=paid_var,
                       bg=self.CARD_BG, fg=self.FG,
                       selectcolor=self.ENTRY_BG,
                       activebackground=self.CARD_BG).pack(side="left")

        def save():
            date_str = fields["date"].get().strip()
            occasion = fields["occasion"].get().strip()
            dt = parse_date(date_str)
            if not dt:
                messagebox.showerror("Invalid Date",
                                     "Use format YYYY-MM-DD", parent=dlg)
                return
            if not occasion:
                messagebox.showerror("Missing", "Occasion name required",
                                     parent=dlg)
                return
            date_iso = dt.strftime("%Y-%m-%d")
            data = {
                "date":     date_iso,
                "occasion": occasion,
                "type":     type_var.get(),
                "paid":     paid_var.get(),
            }
            try:
                from google.cloud import firestore as _fs
                data["created_at"] = _fs.SERVER_TIMESTAMP
            except Exception:
                pass
            self.db.collection("holidays").document(doc_id(date_iso)).set(data)
            messagebox.showinfo("Saved",
                f"✅ {date_iso} — {occasion} saved!", parent=dlg)
            dlg.destroy()
            self._load_holidays()

        tk.Button(dlg, text="💾 Save Holiday", command=save,
                  bg=self.ACCENT, fg="white",
                  font=("Arial", 11, "bold"), relief="flat",
                  padx=16, pady=6).pack(pady=16)

    # ── Bulk import ──────────────────────────────────────────────────────────
    def _bulk_import(self):
        preview = "\n".join(
            f"  {h['date']}  {h['occasion']}  ({h['type']})"
            for h in SEED_HOLIDAYS
        )
        if not messagebox.askyesno(
            "Bulk Import — Oct 2026",
            f"Import these {len(SEED_HOLIDAYS)} holidays?\n\n{preview}"
        ):
            return
        try:
            from google.cloud import firestore as _fs
            batch = self.db.batch()
            for h in SEED_HOLIDAYS:
                ref = self.db.collection("holidays").document(doc_id(h["date"]))
                batch.set(ref, {**h, "created_at": _fs.SERVER_TIMESTAMP})
            batch.commit()
            messagebox.showinfo("Done",
                f"✅ {len(SEED_HOLIDAYS)} holidays imported!")
            self._load_holidays()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ── Month filter ─────────────────────────────────────────────────────────
    def _filter_month(self):
        val = simpledialog.askstring(
            "Filter by Month",
            "Enter month (YYYY-MM), e.g. 2026-10\n(leave blank for all)",
            parent=self.parent
        )
        if val is None:
            return
        val = val.strip()
        if val == "":
            self._load_holidays()
        else:
            try:
                datetime.strptime(val, "%Y-%m")
                self._load_holidays(month_filter=val)
            except ValueError:
                messagebox.showerror("Invalid", "Use format YYYY-MM")

    # ── Delete ───────────────────────────────────────────────────────────────
    def _delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Nothing selected",
                                   "Select a holiday row first.")
            return
        doc_ref_id = sel[0]
        vals = self.tree.item(doc_ref_id, "values")
        if not messagebox.askyesno(
            "Confirm Delete",
            f"Delete holiday:\n{vals[0]} — {vals[2]}?"
        ):
            return
        self.db.collection("holidays").document(doc_ref_id).delete()
        self.tree.delete(doc_ref_id)
        self.status_var.set(f"🗑 Deleted {vals[0]} — {vals[2]}")

    # ── Eligibility check ────────────────────────────────────────────────────
    def _check_eligibility(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Nothing selected",
                                   "Select a holiday row to check.")
            return
        vals   = self.tree.item(sel[0], "values")
        h_date = parse_date(vals[0])
        if not h_date:
            return
        window = [
            (h_date + timedelta(days=d)).strftime("%Y-%m-%d")
            for d in range(-2, 3)
        ]

        dlg = tk.Toplevel(self.parent)
        dlg.title(f"Eligibility — {vals[2]} ({vals[0]})")
        dlg.geometry("520x420")
        dlg.configure(bg=self.CARD_BG)

        tk.Label(dlg,
                 text=f"🎉 {vals[2]}  —  {vals[0]}",
                 bg=self.CARD_BG, fg=self.ACCENT,
                 font=("Arial", 13, "bold")).pack(pady=12)
        tk.Label(dlg,
                 text=f"Checking attendance window: {window[0]}  →  {window[-1]}",
                 bg=self.CARD_BG, fg="#aaa",
                 font=("Arial", 9)).pack()

        cols2 = ("status", "id", "name")
        tv = ttk.Treeview(dlg, columns=cols2, show="headings")
        for c, w in [("status", 130), ("id", 140), ("name", 200)]:
            tv.heading(c, text=c.capitalize())
            tv.column(c, width=w, anchor="center")
        tv.pack(fill="both", expand=True, padx=12, pady=8)

        status_lbl = tk.Label(dlg, text="Checking...",
                              bg=self.CARD_BG, fg="#888",
                              font=("Arial", 9))
        status_lbl.pack(pady=4)

        def run_check():
            eligible = 0
            ineligible = 0
            try:
                employees = {
                    d.id: d.to_dict().get("name", d.id)
                    for d in self.db.collection("employees").stream()
                }
                for emp_id, emp_name in employees.items():
                    found = False
                    for w_date in window:
                        month_key = w_date[:7]
                        docs = (
                            self.db.collection("attendance")
                            .document(month_key)
                            .collection(emp_id)
                            .where("date", "==", w_date)
                            .where("type", "in", ["IN", "COMPLETE"])
                            .limit(1)
                            .stream()
                        )
                        if any(True for _ in docs):
                            found = True
                            break
                    if found:
                        tv.insert("", "end",
                            values=("✅ Eligible", emp_id, emp_name),
                            tags=("yes",))
                        eligible += 1
                    else:
                        tv.insert("", "end",
                            values=("❌ Not Eligible", emp_id, emp_name),
                            tags=("no",))
                        ineligible += 1
                tv.tag_configure("yes", foreground="#27ae60")
                tv.tag_configure("no",  foreground="#c0392b")
                status_lbl.config(
                    text=f"✅ Eligible: {eligible}   ❌ Not Eligible: {ineligible}")
            except Exception as e:
                status_lbl.config(text=f"❌ Error: {e}")

        dlg.after(100, run_check)
