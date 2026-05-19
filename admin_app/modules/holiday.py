"""
Hype HR — Paid Holiday Manager Module (Tkinter GUI)
Developed by David | Nexuzy Lab

Part of admin_app. Registered as '🎉 Holidays' tab in main.py.

All holidays are entered MANUALLY by the admin — no pre-loaded seed data.

Features:
  - Add single holiday via form (date, occasion, type, paid toggle)
  - Add Multiple Holidays in one session — admin keeps adding without closing
  - List all holidays with colour-coded type badges
  - Filter / view by month (e.g. show only August holidays)
  - Delete selected holiday
  - Eligibility check — employees with attendance ±2 days earn paid holiday

Firestore structure:
  holidays/{YYYYMMDD}/
    date      : "YYYY-MM-DD"
    occasion  : "Happy New Year"
    type      : "Festival" | "National" | "Optional" | "Restricted"
    paid      : true
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, timedelta
from utils.firebase_client import get_firestore_client

# ── Type colours ──────────────────────────────────────────────────────────
TYPE_COLORS = {
    "Festival":   "#f77f00",
    "National":   "#27ae60",
    "Optional":   "#2980b9",
    "Restricted": "#c0392b",
}
HOLIDAY_TYPES = ["Festival", "National", "Optional", "Restricted"]


def doc_id(date_str: str) -> str:
    """20260115 style doc ID for easy Firestore ordering."""
    return date_str.replace("-", "")


def parse_date(s: str):
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d %m %Y"):
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
    GREEN    = "#27ae60"
    RED      = "#c0392b"

    def __init__(self, parent, current_user=None):
        self.parent = parent
        self.user   = current_user or {}
        self.db     = get_firestore_client()
        self._build_ui()
        self._load_holidays()

    # ── UI ──────────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.parent.configure(bg=self.BG)

        # ─ Toolbar
        toolbar = tk.Frame(self.parent, bg=self.CARD_BG, pady=8)
        toolbar.pack(fill="x", padx=10, pady=(10, 0))

        tk.Label(toolbar, text="🎉 Paid Holiday Manager",
                 font=("Arial", 14, "bold"),
                 bg=self.CARD_BG, fg=self.ACCENT).pack(side="left", padx=12)

        for txt, cmd, color in [
            ("➕ Add Holiday",         self._open_add_dialog,  self.ACCENT),
            ("🗓 Add Multiple",        self._open_multi_dialog, "#8e44ad"),
            ("🔍 Filter by Month",      self._filter_month,      "#2980b9"),
            ("🗑 Delete Selected",      self._delete_selected,   self.RED),
            ("👥 Check Eligibility",    self._check_eligibility, self.GREEN),
            ("🔄 Refresh",             self._load_holidays,     "#555"),
        ]:
            tk.Button(
                toolbar, text=txt, command=cmd,
                bg=color, fg=self.BTN_FG,
                font=("Arial", 9, "bold"), relief="flat",
                padx=10, pady=4, cursor="hand2"
            ).pack(side="right", padx=4)

        # ─ Treeview
        tree_frame = tk.Frame(self.parent, bg=self.BG)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        cols = ("date", "day", "occasion", "type", "paid")
        self.tree = ttk.Treeview(tree_frame, columns=cols,
                                 show="headings", selectmode="browse")

        s = ttk.Style()
        s.configure("Treeview",
                    background=self.CARD_BG, foreground=self.FG,
                    fieldbackground=self.CARD_BG, rowheight=30,
                    font=("Arial", 10))
        s.configure("Treeview.Heading",
                    background=self.ACCENT, foreground="white",
                    font=("Arial", 10, "bold"))
        s.map("Treeview", background=[("selected", self.SEL_BG)])

        for col, head, w in [
            ("date",    "Date",     120),
            ("day",     "Day",      100),
            ("occasion","Occasion", 220),
            ("type",    "Type",     110),
            ("paid",    "Paid",      80),
        ]:
            self.tree.heading(col, text=head)
            self.tree.column(col, width=w, anchor="center")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",
                            command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        # ─ Status bar
        self.status_var = tk.StringVar(value="Loading holidays...")
        tk.Label(self.parent, textvariable=self.status_var,
                 bg=self.BG, fg="#888",
                 font=("Arial", 9)).pack(anchor="w", padx=12, pady=(0, 6))

    # ── Load from Firestore ───────────────────────────────────────────────────
    def _load_holidays(self, month_filter=None):
        self.tree.delete(*self.tree.get_children())
        try:
            q = self.db.collection("holidays").order_by("date")
            if month_filter:
                q = (q.where("date", ">=", f"{month_filter}-01")
                      .where("date", "<=", f"{month_filter}-31"))
            count = 0
            for doc in q.stream():
                h      = doc.to_dict()
                dt     = parse_date(h.get("date", ""))
                day_nm = dt.strftime("%A") if dt else ""
                paid   = "✅ Yes" if h.get("paid") else "❌ No"
                htype  = h.get("type", "")
                tag    = htype.lower()
                self.tree.insert("", "end", iid=doc.id,
                    values=(h["date"], day_nm, h.get("occasion", ""), htype, paid),
                    tags=(tag,))
                self.tree.tag_configure(tag,
                    foreground=TYPE_COLORS.get(htype, self.FG))
                count += 1
            suffix = f"month {month_filter}" if month_filter else "all"
            self.status_var.set(f"✅ {count} holiday(s) — {suffix}")
        except Exception as e:
            self.status_var.set(f"❌ Error: {e}")

    # ── Shared form builder ─────────────────────────────────────────────────
    def _make_form(self, parent, date_default=""):
        """
        Build a holiday entry form inside `parent`.
        Returns a dict with refs to all input widgets + type_var + paid_var.
        """
        fields = {}

        def lbl_row(text):
            r = tk.Frame(parent, bg=self.CARD_BG)
            r.pack(fill="x", padx=20, pady=5)
            tk.Label(r, text=text, bg=self.CARD_BG, fg=self.FG,
                     font=("Arial", 10), width=16, anchor="w").pack(side="left")
            return r

        def mk_entry(row_frame, default=""):
            e = tk.Entry(row_frame, bg=self.ENTRY_BG, fg=self.FG,
                         insertbackground=self.FG, relief="flat",
                         font=("Arial", 10))
            e.pack(side="left", fill="x", expand=True)
            if default:
                e.insert(0, default)
            return e

        r1 = lbl_row("Date (YYYY-MM-DD)")
        fields["date"] = mk_entry(r1, date_default or datetime.today().strftime("%Y-%m-%d"))

        r2 = lbl_row("Occasion / Name")
        fields["occasion"] = mk_entry(r2, "")

        r3 = lbl_row("Type")
        type_var = tk.StringVar(value="National")
        fields["type_var"] = type_var
        ttk.Combobox(r3, textvariable=type_var,
                     values=HOLIDAY_TYPES,
                     state="readonly", width=18).pack(side="left")

        r4 = lbl_row("Paid Holiday")
        paid_var = tk.BooleanVar(value=True)
        fields["paid_var"] = paid_var
        tk.Checkbutton(r4, variable=paid_var,
                       bg=self.CARD_BG, fg=self.FG,
                       selectcolor=self.ENTRY_BG,
                       activebackground=self.CARD_BG,
                       text="Yes (tick = paid)",
                       font=("Arial", 10)).pack(side="left")

        return fields

    def _save_one(self, fields, parent_dlg, clear_after=False, msg_widget=None):
        """
        Validate + save one holiday from a form dict.
        Returns True on success, False on validation failure.
        """
        date_str = fields["date"].get().strip()
        occasion = fields["occasion"].get().strip()
        dt = parse_date(date_str)
        if not dt:
            messagebox.showerror("Invalid Date",
                "Enter date as YYYY-MM-DD, e.g. 2026-01-01",
                parent=parent_dlg)
            return False
        if not occasion:
            messagebox.showerror("Missing Occasion",
                "Please enter the holiday name / occasion.",
                parent=parent_dlg)
            return False

        date_iso = dt.strftime("%Y-%m-%d")
        data = {
            "date":     date_iso,
            "occasion": occasion,
            "type":     fields["type_var"].get(),
            "paid":     fields["paid_var"].get(),
        }
        try:
            from google.cloud import firestore as _fs
            data["created_at"] = _fs.SERVER_TIMESTAMP
        except Exception:
            pass

        self.db.collection("holidays").document(doc_id(date_iso)).set(data)

        if msg_widget:
            msg_widget.config(
                text=f"✅ Saved: {date_iso} — {occasion}",
                fg=self.GREEN)

        if clear_after:
            fields["date"].delete(0, "end")
            fields["date"].insert(0, "")
            fields["occasion"].delete(0, "end")
            fields["type_var"].set("National")
            fields["paid_var"].set(True)
            fields["date"].focus()

        return True

    # ── Add single holiday dialog ─────────────────────────────────────────
    def _open_add_dialog(self):
        dlg = tk.Toplevel(self.parent)
        dlg.title("➕ Add Holiday")
        dlg.geometry("440x320")
        dlg.configure(bg=self.CARD_BG)
        dlg.grab_set()

        tk.Label(dlg, text="Add Holiday",
                 bg=self.CARD_BG, fg=self.ACCENT,
                 font=("Arial", 13, "bold")).pack(pady=(14, 4))

        fields = self._make_form(dlg)

        msg_lbl = tk.Label(dlg, text="", bg=self.CARD_BG, font=("Arial", 9))
        msg_lbl.pack()

        def save_and_close():
            if self._save_one(fields, dlg, msg_widget=msg_lbl):
                self._load_holidays()
                dlg.after(800, dlg.destroy)

        tk.Button(dlg, text="💾 Save Holiday",
                  command=save_and_close,
                  bg=self.ACCENT, fg="white",
                  font=("Arial", 11, "bold"), relief="flat",
                  padx=16, pady=6).pack(pady=12)

    # ── Add MULTIPLE holidays dialog ─────────────────────────────────────
    def _open_multi_dialog(self):
        """
        Admin can keep entering holidays one-by-one without closing the dialog.
        Each saved entry appears in the saved list at the bottom.
        'Done' closes and refreshes the main table.
        """
        dlg = tk.Toplevel(self.parent)
        dlg.title("🗓 Add Multiple Holidays")
        dlg.geometry("500x560")
        dlg.configure(bg=self.CARD_BG)
        dlg.grab_set()

        tk.Label(dlg, text="Add Multiple Holidays",
                 bg=self.CARD_BG, fg=self.ACCENT,
                 font=("Arial", 13, "bold")).pack(pady=(14, 2))
        tk.Label(dlg,
                 text="Fill in the form → click \u2018Save & Add Another\u2019 for each holiday.",
                 bg=self.CARD_BG, fg="#aaa",
                 font=("Arial", 9)).pack()

        # Form
        form_frame = tk.Frame(dlg, bg=self.CARD_BG)
        form_frame.pack(fill="x", pady=6)
        fields = self._make_form(form_frame)

        # Status message
        msg_lbl = tk.Label(dlg, text="", bg=self.CARD_BG,
                           font=("Arial", 9))
        msg_lbl.pack()

        # Saved-items list
        tk.Label(dlg, text="— Saved in this session —",
                 bg=self.CARD_BG, fg="#666",
                 font=("Arial", 8)).pack(pady=(6, 0))

        saved_box = tk.Listbox(
            dlg, bg=self.ENTRY_BG, fg="#aaffaa",
            font=("Arial", 9), height=6,
            selectbackground=self.SEL_BG, relief="flat"
        )
        saved_box.pack(fill="x", padx=20, pady=4)

        saved_count = [0]   # mutable counter

        def save_and_next():
            occasion = fields["occasion"].get().strip()
            date_str = fields["date"].get().strip()
            ok = self._save_one(fields, dlg,
                                clear_after=True,
                                msg_widget=msg_lbl)
            if ok:
                saved_count[0] += 1
                dt = parse_date(date_str)
                date_iso = dt.strftime("%Y-%m-%d") if dt else date_str
                saved_box.insert("end",
                    f"  ✅  {date_iso}  —  {occasion}  "
                    f"({fields['type_var'].get()})")
                saved_box.yview_moveto(1)  # scroll to bottom

        def done():
            self._load_holidays()
            dlg.destroy()

        btn_row = tk.Frame(dlg, bg=self.CARD_BG)
        btn_row.pack(pady=8)

        tk.Button(btn_row,
                  text="💾 Save & Add Another",
                  command=save_and_next,
                  bg="#8e44ad", fg="white",
                  font=("Arial", 11, "bold"), relief="flat",
                  padx=14, pady=6).pack(side="left", padx=8)

        tk.Button(btn_row,
                  text="✔ Done",
                  command=done,
                  bg=self.GREEN, fg="white",
                  font=("Arial", 11, "bold"), relief="flat",
                  padx=14, pady=6).pack(side="left", padx=8)

    # ── Filter by month ─────────────────────────────────────────────────────
    def _filter_month(self):
        val = simpledialog.askstring(
            "Filter by Month",
            "Enter YYYY-MM  (e.g. 2026-08 for August)\n"
            "Leave blank to show all holidays.",
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
                messagebox.showerror("Invalid Format",
                    "Please use YYYY-MM, e.g. 2026-08")

    # ── Delete ─────────────────────────────────────────────────────────────────
    def _delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Nothing Selected",
                "Click on a holiday row first, then press Delete.")
            return
        vals = self.tree.item(sel[0], "values")
        if not messagebox.askyesno(
            "Confirm Delete",
            f"Permanently delete:\n\n  {vals[0]}  —  {vals[2]}?"
        ):
            return
        self.db.collection("holidays").document(sel[0]).delete()
        self.tree.delete(sel[0])
        self.status_var.set(f"🗑 Deleted: {vals[0]} — {vals[2]}")

    # ── Eligibility check popup ────────────────────────────────────────────
    def _check_eligibility(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Nothing Selected",
                "Select a holiday row to check eligibility.")
            return
        vals   = self.tree.item(sel[0], "values")
        h_date = parse_date(vals[0])
        if not h_date:
            return

        window = [
            (h_date + timedelta(days=d)).strftime("%Y-%m-%d")
            for d in range(-2, 3)   # -2, -1, 0, +1, +2
        ]

        dlg = tk.Toplevel(self.parent)
        dlg.title(f"Eligibility — {vals[2]}")
        dlg.geometry("520x440")
        dlg.configure(bg=self.CARD_BG)

        tk.Label(dlg, text=f"🎉 {vals[2]}",
                 bg=self.CARD_BG, fg=self.ACCENT,
                 font=("Arial", 13, "bold")).pack(pady=(14, 2))
        tk.Label(dlg, text=f"Date: {vals[0]}    Type: {vals[3]}    Paid: {vals[4]}",
                 bg=self.CARD_BG, fg="#ccc",
                 font=("Arial", 9)).pack()
        tk.Label(dlg,
                 text=f"Attendance window checked: "
                      f"{window[0]}  →  {window[-1]}",
                 bg=self.CARD_BG, fg="#888",
                 font=("Arial", 9)).pack(pady=(2, 6))

        tv = ttk.Treeview(dlg, columns=("status", "id", "name"),
                          show="headings")
        for c, w in [("status", 130), ("id", 140), ("name", 200)]:
            tv.heading(c, text=c.capitalize())
            tv.column(c, width=w, anchor="center")
        tv.pack(fill="both", expand=True, padx=12, pady=4)

        info = tk.Label(dlg, text="⌛ Checking...",
                        bg=self.CARD_BG, fg="#888", font=("Arial", 9))
        info.pack(pady=6)

        def run():
            ok = err = 0
            try:
                emps = {d.id: d.to_dict().get("name", d.id)
                        for d in self.db.collection("employees").stream()}
                for eid, ename in emps.items():
                    found = False
                    for wd in window:
                        docs = (
                            self.db.collection("attendance")
                            .document(wd[:7])
                            .collection(eid)
                            .where("date", "==", wd)
                            .where("type", "in", ["IN", "COMPLETE"])
                            .limit(1).stream()
                        )
                        if any(True for _ in docs):
                            found = True
                            break
                    if found:
                        tv.insert("", "end",
                            values=("✅ Eligible", eid, ename), tags=("yes",))
                        ok += 1
                    else:
                        tv.insert("", "end",
                            values=("❌ Not Eligible", eid, ename), tags=("no",))
                        err += 1
                tv.tag_configure("yes", foreground=self.GREEN)
                tv.tag_configure("no",  foreground=self.RED)
                info.config(
                    text=f"✅ Eligible: {ok}     ❌ Not Eligible: {err}",
                    fg=self.FG)
            except Exception as e:
                info.config(text=f"❌ Error: {e}", fg=self.RED)

        dlg.after(120, run)
