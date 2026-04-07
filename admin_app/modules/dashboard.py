"""
Live Dashboard — Hype HR Management
KPIs: Total Employees, Present Today, Absent, Inside Now
Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
import tkinter as tk
from tkinter import ttk
from datetime import datetime, date
from utils.firebase_config import get_db


class DashboardModule:
    def __init__(self, parent_frame, current_user):
        self.parent = parent_frame
        self.current_user = current_user
        self.db = get_db()
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        header = tk.Frame(self.parent, bg="#1a2740", pady=10)
        header.pack(fill="x")
        tk.Label(header, text="📊 Live Dashboard",
                 font=("Arial", 15, "bold"), bg="#1a2740", fg="white").pack(side="left", padx=15)
        self.clock_label = tk.Label(header, font=("Arial", 12), bg="#1a2740", fg="#f77f00")
        self.clock_label.pack(side="right", padx=15)
        self._update_clock()

        kpi_frame = tk.Frame(self.parent, bg="#0d1b2a")
        kpi_frame.pack(fill="x", padx=15, pady=10)
        self.kpi_vars = {}
        kpis = [
            ("Total Employees",  "total_emp",     "#1e6f9f"),
            ("Present Today",    "present_today", "#2e8b57"),
            ("Absent Today",     "absent_today",  "#c0392b"),
            ("Inside Right Now", "inside_now",    "#8e44ad"),
        ]
        for i, (label, key, color) in enumerate(kpis):
            card = tk.Frame(kpi_frame, bg=color, padx=20, pady=15)
            card.grid(row=0, column=i, padx=8, ipadx=10)
            self.kpi_vars[key] = tk.StringVar(value="—")
            tk.Label(card, textvariable=self.kpi_vars[key],
                     font=("Arial", 24, "bold"), bg=color, fg="white").pack()
            tk.Label(card, text=label, font=("Arial", 9), bg=color, fg="#ddd").pack()

        tk.Label(self.parent, text="🟢 Employees Currently Inside",
                 font=("Arial", 12, "bold"), bg="#0d1b2a", fg="white").pack(anchor="w", padx=15, pady=(10, 3))
        cols = ("Employee ID", "Name", "IN Time", "Location")
        self.inside_tree = ttk.Treeview(self.parent, columns=cols, show="headings", height=7)
        for col in cols:
            self.inside_tree.heading(col, text=col)
            self.inside_tree.column(col, width=155, anchor="center")
        self.inside_tree.pack(fill="x", padx=15)

        tk.Label(self.parent, text="🕐 Recent Activity",
                 font=("Arial", 12, "bold"), bg="#0d1b2a", fg="white").pack(anchor="w", padx=15, pady=(10, 3))
        cols2 = ("Time", "Employee ID", "Name", "Action", "Location")
        self.activity_tree = ttk.Treeview(self.parent, columns=cols2, show="headings", height=6)
        for col in cols2:
            self.activity_tree.heading(col, text=col)
            self.activity_tree.column(col, width=130, anchor="center")
        self.activity_tree.pack(fill="x", padx=15)

        tk.Button(self.parent, text="🔄 Refresh", bg="#1e3a5f", fg="white", relief="flat",
                  padx=10, pady=5, cursor="hand2", command=self._refresh).pack(pady=8)

    def _update_clock(self):
        self.clock_label.config(text=datetime.now().strftime("%A, %d %B %Y  %H:%M:%S"))
        self.parent.after(1000, self._update_clock)

    def _refresh(self):
        try:
            db = self.db
            today = str(date.today())
            emp_count = len(list(db.collection("employees").where("status", "==", "active").stream()))
            self.kpi_vars["total_emp"].set(str(emp_count))
            sessions = list(db.collection("sessions").where("date", "==", today).stream())
            present = sum(1 for s in sessions if s.to_dict().get("status") in ("Full Day", "Half Day"))
            self.kpi_vars["present_today"].set(str(present))
            self.kpi_vars["absent_today"].set(str(emp_count - present))

            for row in self.inside_tree.get_children(): self.inside_tree.delete(row)
            logs = list(db.collection("attendance_logs").where("date", "==", today).stream())
            emp_states = {}
            for log in sorted(logs, key=lambda x: x.to_dict().get("timestamp", "")):
                d = log.to_dict()
                emp_states[d["employee_id"]] = d
            inside_count = 0
            for emp_id, last_log in emp_states.items():
                if last_log.get("action") == "IN":
                    emp_doc = db.collection("employees").document(emp_id).get()
                    emp_name = emp_doc.to_dict().get("name", "") if emp_doc.exists else ""
                    ts = str(last_log.get("timestamp", ""))
                    self.inside_tree.insert("", "end", values=(emp_id, emp_name, ts[11:16], last_log.get("location", "")))
                    inside_count += 1
            self.kpi_vars["inside_now"].set(str(inside_count))

            for row in self.activity_tree.get_children(): self.activity_tree.delete(row)
            recent = list(db.collection("attendance_logs").order_by("timestamp", direction="DESCENDING").limit(20).stream())
            for log in recent:
                l = log.to_dict()
                emp_doc = db.collection("employees").document(l.get("employee_id", "")).get()
                emp_name = emp_doc.to_dict().get("name", "") if emp_doc.exists else ""
                ts = str(l.get("timestamp", ""))
                action = l.get("action", "")
                tag = "in_t" if action == "IN" else "out_t"
                self.activity_tree.insert("", "end", values=(
                    ts[11:16], l.get("employee_id", ""), emp_name, action, l.get("location", "")
                ), tags=(tag,))
            self.activity_tree.tag_configure("in_t",  foreground="#00cc66")
            self.activity_tree.tag_configure("out_t", foreground="#ff8844")
        except Exception as e:
            print(f"Dashboard error: {e}")
