"""
Security Guard Module — Hype HR Management
For employees WITHOUT smartphones — Security Guard scans their ID card QR
using the PC/laptop webcam and marks IN/OUT attendance.

Features:
  - Live webcam QR scanner (cv2 + pyzbar)
  - Manual Employee ID entry fallback (no webcam needed)
  - Auto IN/OUT toggle per employee per day
  - Logs to Firestore: attendance_logs + sessions
  - Shows today’s scan log live
  - Works offline with local log saved to security_log.csv
Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
from utils.firebase_config import get_db
from utils.db import read_all
import threading, csv, os

LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "security_log.csv")


def _now_str():  return datetime.now().strftime("%H:%M:%S")
def _today():    return str(date.today())


class SecurityModule:
    def __init__(self, parent_frame, current_user):
        self.parent       = parent_frame
        self.current_user = current_user
        self.db           = get_db()
        self.scanning     = False
        self.cap          = None
        self._emp_cache   = {}       # employee_id -> name
        self._build_ui()
        self._refresh_emp_cache()
        self._load_today_log()

    # ──────────────────────── UI ───────────────────────────────────
    def _build_ui(self):
        # Header
        top = tk.Frame(self.parent, bg="#1a2740")
        top.pack(fill="x", pady=(0, 6))
        tk.Label(top, text="🛡️ Security Guard — Attendance Scanner",
                 font=("Arial", 14, "bold"), bg="#1a2740", fg="white").pack(side="left", padx=10)
        tk.Label(top, text=f"Guard: {self.current_user.get('display_name','')}",
                 bg="#1a2740", fg="#aaa", font=("Arial", 9)).pack(side="right", padx=10)

        # Two columns: left=scanner, right=log
        body = tk.Frame(self.parent, bg="#0d1b2a")
        body.pack(fill="both", expand=True, padx=8, pady=4)

        left  = tk.Frame(body, bg="#0d1b2a", width=380)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)

        right = tk.Frame(body, bg="#0d1b2a")
        right.pack(side="left", fill="both", expand=True)

        self._build_scanner_panel(left)
        self._build_log_panel(right)

    def _build_scanner_panel(self, parent):
        # Date banner
        tk.Label(parent,
                 text=f"📅  Today: {_today()}",
                 bg="#1a2740", fg="#f0c040",
                 font=("Arial", 11, "bold")).pack(fill="x", pady=(0, 8))

        # Webcam preview canvas
        self.cam_canvas = tk.Canvas(parent, width=340, height=256,
                                    bg="#07111c", highlightthickness=1,
                                    highlightbackground="#2c3e50")
        self.cam_canvas.pack(pady=4)
        self.cam_canvas.create_text(170, 128, text="📷  Camera feed will appear here",
                                    fill="#555", font=("Arial", 11))

        # Camera buttons
        cam_btns = tk.Frame(parent, bg="#0d1b2a")
        cam_btns.pack(fill="x", pady=4)
        self.start_btn = tk.Button(cam_btns, text="▶ Start Camera Scanner",
                                   bg="#27ae60", fg="white", relief="flat",
                                   font=("Arial", 9, "bold"), padx=12, pady=6,
                                   cursor="hand2", command=self._start_camera)
        self.start_btn.pack(side="left", padx=(0, 6))
        self.stop_btn = tk.Button(cam_btns, text="■ Stop",
                                  bg="#c0392b", fg="white", relief="flat",
                                  padx=10, pady=6, state="disabled",
                                  command=self._stop_camera)
        self.stop_btn.pack(side="left")

        # Status
        self.scan_status = tk.Label(parent, text="🔴  Scanner stopped",
                                    bg="#0d1b2a", fg="#e74c3c",
                                    font=("Arial", 10, "bold"))
        self.scan_status.pack(pady=4)

        # Last scan result
        self.last_scan_frm = tk.Frame(parent, bg="#132030", padx=14, pady=12)
        self.last_scan_frm.pack(fill="x", pady=6)
        tk.Label(self.last_scan_frm, text="Last Scanned Employee",
                 bg="#132030", fg="#aaa", font=("Arial", 8)).pack(anchor="w")
        self.last_emp_lbl = tk.Label(self.last_scan_frm, text="—",
                                     bg="#132030", fg="#f0c040",
                                     font=("Arial", 13, "bold"))
        self.last_emp_lbl.pack(anchor="w")
        self.last_action_lbl = tk.Label(self.last_scan_frm, text="",
                                        bg="#132030", fg="#27ae60",
                                        font=("Arial", 11))
        self.last_action_lbl.pack(anchor="w")
        self.last_time_lbl = tk.Label(self.last_scan_frm, text="",
                                      bg="#132030", fg="#aaa",
                                      font=("Arial", 9))
        self.last_time_lbl.pack(anchor="w")

        # ─ Manual entry fallback
        tk.Frame(parent, height=1, bg="#2c3e50").pack(fill="x", pady=10)
        tk.Label(parent, text="🔢 Manual Entry (no webcam / backup)",
                 bg="#0d1b2a", fg="#f0c040",
                 font=("Arial", 9, "bold")).pack(anchor="w")

        mid = tk.Frame(parent, bg="#0d1b2a"); mid.pack(fill="x", pady=4)
        tk.Label(mid, text="Employee ID:", bg="#0d1b2a", fg="#ccc").pack(side="left")
        self.manual_var = tk.StringVar()
        manual_entry = tk.Entry(mid, textvariable=self.manual_var, width=14,
                                bg="#1e3a5f", fg="white",
                                insertbackground="white", relief="flat", bd=4,
                                font=("Arial", 11))
        manual_entry.pack(side="left", padx=6)
        manual_entry.bind("<Return>", lambda e: self._manual_mark())
        tk.Button(mid, text="✔ Mark IN/OUT",
                  bg="#f77f00", fg="white", relief="flat",
                  font=("Arial", 9, "bold"), padx=10, pady=4,
                  cursor="hand2", command=self._manual_mark).pack(side="left")

        # Manual override buttons
        ov = tk.Frame(parent, bg="#0d1b2a"); ov.pack(fill="x", pady=3)
        tk.Button(ov, text="Force IN",  bg="#27ae60", fg="white",
                  relief="flat", padx=8, pady=3,
                  command=lambda: self._manual_mark(force="IN")).pack(side="left", padx=(0, 4))
        tk.Button(ov, text="Force OUT", bg="#c0392b", fg="white",
                  relief="flat", padx=8, pady=3,
                  command=lambda: self._manual_mark(force="OUT")).pack(side="left")

        self.manual_status = tk.Label(parent, text="",
                                      bg="#0d1b2a", fg="#27ae60",
                                      font=("Arial", 9))
        self.manual_status.pack(anchor="w")

    def _build_log_panel(self, parent):
        hdr = tk.Frame(parent, bg="#1a2740")
        hdr.pack(fill="x", pady=(0, 4))
        tk.Label(hdr, text="📋 Today’s Scan Log",
                 bg="#1a2740", fg="#f0c040",
                 font=("Arial", 11, "bold")).pack(side="left", padx=8, pady=4)
        tk.Button(hdr, text="🔄 Refresh", bg="#555", fg="white",
                  relief="flat", padx=8, pady=3,
                  command=self._load_today_log).pack(side="right", padx=6)

        cols = ("time", "emp_id", "name", "action", "method")
        self.log_tree = ttk.Treeview(parent, columns=cols,
                                     show="headings", height=28)
        for col, lbl, w in [
            ("time",   "Time",       90),
            ("emp_id", "Emp ID",    100),
            ("name",   "Name",      160),
            ("action", "IN / OUT",   80),
            ("method", "Method",    100),
        ]:
            self.log_tree.heading(col, text=lbl)
            self.log_tree.column(col, width=w, anchor="center")
        self.log_tree.pack(fill="both", expand=True, padx=4)
        self.log_tree.tag_configure("in",  foreground="#00cc66")
        self.log_tree.tag_configure("out", foreground="#ff6644")

        self.log_count_lbl = tk.Label(parent, text="",
                                      bg="#0d1b2a", fg="#aaa",
                                      font=("Arial", 8))
        self.log_count_lbl.pack(anchor="w", padx=4)

    # ────────────────── EMPLOYEE CACHE ───────────────────────
    def _refresh_emp_cache(self):
        for e in read_all("employees"):
            self._emp_cache[e.get("employee_id", "")] = e.get("name", "Unknown")

    # ────────────────── WEBCAM SCANNER ──────────────────────
    def _start_camera(self):
        try:
            import cv2
        except ImportError:
            messagebox.showerror("Missing Package",
                "OpenCV is required for camera scanning.\n\n"
                "Run: pip install opencv-python pyzbar\n\n"
                "Use Manual Entry below as fallback.", parent=self.parent)
            return
        self.scanning = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.scan_status.config(text="🟢  Scanner running — show ID card QR to camera",
                                fg="#27ae60")
        t = threading.Thread(target=self._camera_loop, daemon=True)
        t.start()

    def _stop_camera(self):
        self.scanning = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.scan_status.config(text="🔴  Scanner stopped", fg="#e74c3c")
        self.cam_canvas.delete("all")
        self.cam_canvas.create_text(170, 128,
            text="📷  Camera feed will appear here",
            fill="#555", font=("Arial", 11))

    def _camera_loop(self):
        import cv2
        from pyzbar import pyzbar
        from PIL import Image, ImageTk

        self.cap = cv2.VideoCapture(0)
        last_scanned = None
        last_scan_time = 0

        while self.scanning and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret: break

            # Decode QR codes
            decoded = pyzbar.decode(frame)
            for obj in decoded:
                emp_id = obj.data.decode("utf-8").strip().upper()
                now_ts = datetime.now().timestamp()
                # Debounce: same employee not re-scanned within 3s
                if emp_id != last_scanned or (now_ts - last_scan_time) > 3:
                    last_scanned = emp_id
                    last_scan_time = now_ts
                    self.parent.after(0, lambda e=emp_id: self._process_scan(e, "CAMERA"))
                # Draw green box on detected QR
                pts = obj.polygon
                if len(pts) == 4:
                    import numpy as np
                    pts = np.array([(p.x, p.y) for p in pts], dtype=np.int32)
                    cv2.polylines(frame, [pts], True, (0, 255, 80), 3)

            # Show frame on canvas
            rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img   = Image.fromarray(rgb).resize((340, 256))
            photo = ImageTk.PhotoImage(img)
            self.parent.after(0, lambda p=photo: self._update_canvas(p))

        if self.cap:
            self.cap.release()
            self.cap = None

    def _update_canvas(self, photo):
        self.cam_canvas.delete("all")
        self.cam_canvas.create_image(0, 0, anchor="nw", image=photo)
        self.cam_canvas._photo = photo   # prevent GC

    # ────────────────── CORE: PROCESS SCAN ───────────────────
    def _process_scan(self, emp_id: str, method: str = "CAMERA"):
        emp_id = emp_id.strip().upper()
        if not emp_id:
            return
        name = self._emp_cache.get(emp_id, "")
        if not name:
            # Try fetching from Firestore
            try:
                doc = self.db.collection("employees").document(emp_id).get()
                if doc.exists:
                    name = doc.to_dict().get("name", "Unknown")
                    self._emp_cache[emp_id] = name
                else:
                    self.manual_status.config(
                        text=f"❌ Employee '{emp_id}' not found.", fg="#e74c3c")
                    return
            except Exception as ex:
                self.manual_status.config(text=f"Error: {ex}", fg="#e74c3c")
                return

        # Determine IN or OUT
        action = self._determine_action(emp_id)
        ts     = datetime.now().isoformat()
        tod    = _today()
        time_s = _now_str()

        # Write to Firestore attendance_logs
        try:
            self.db.collection("attendance_logs").add({
                "employee_id": emp_id,
                "timestamp":   ts,
                "action":      action,
                "session":     1,
                "location":    "Security Gate",
                "method":      method,
                "scanned_by":  self.current_user.get("username", "security"),
            })
            # Update session
            self._update_session(emp_id, tod, action, time_s)
        except Exception as ex:
            # Save to local CSV as fallback
            self._save_local_log(emp_id, name, action, tod, time_s, method)
            self.manual_status.config(
                text=f"⚠️ Saved locally (Firestore error: {ex})", fg="#e67e22")

        # Update UI
        colour  = "#00cc66" if action == "IN" else "#ff6644"
        emoji   = "✅" if action == "IN" else "🚪"
        self.last_emp_lbl.config(text=f"{name}  ({emp_id})")
        self.last_action_lbl.config(
            text=f"{emoji}  Marked {action}", fg=colour)
        self.last_time_lbl.config(text=f"Time: {time_s}")
        self.manual_status.config(
            text=f"✔ {emp_id} — {name} — {action} at {time_s}",
            fg=colour)
        self.manual_var.set("")

        # Add to live log tree (top)
        self.log_tree.insert("", 0,
            values=(time_s, emp_id, name, action, method),
            tags=("in" if action == "IN" else "out",))

        # Append to local CSV
        self._save_local_log(emp_id, name, action, tod, time_s, method)

    def _determine_action(self, emp_id: str) -> str:
        """Check today’s logs: if last action was IN → OUT, else → IN."""
        tod = _today()
        try:
            logs = self.db.collection("attendance_logs") \
                .where("employee_id", "==", emp_id) \
                .where("timestamp", ">=", tod + "T00:00:00") \
                .order_by("timestamp", direction="DESCENDING") \
                .limit(1).stream()
            for doc in logs:
                last = doc.to_dict().get("action", "OUT")
                return "OUT" if last == "IN" else "IN"
        except Exception:
            pass
        return "IN"   # default first scan = IN

    def _update_session(self, emp_id: str, date_str: str,
                        action: str, time_str: str):
        """Update or create today’s session record."""
        doc_id  = f"{emp_id}_{date_str}"
        ref     = self.db.collection("sessions").document(doc_id)
        existing = ref.get()
        if existing.exists:
            updates = {"updated_at": datetime.now().isoformat()}
            if action == "IN":
                updates["in_time"] = time_str
            else:
                updates["out_time"] = time_str
                # Calculate duty hours and classify
                data     = existing.to_dict()
                in_time  = data.get("in_time", "")
                if in_time and in_time != "—":
                    try:
                        fmt  = "%H:%M:%S"
                        diff = (datetime.strptime(time_str, fmt) -
                                datetime.strptime(in_time, fmt)).seconds / 3600
                        if diff < 4:
                            updates["duty_status"] = "absent"
                        elif diff < 7:
                            updates["duty_status"] = "half"
                        else:
                            updates["duty_status"] = "full"
                        updates["duty_hours"] = round(diff, 2)
                    except Exception:
                        pass
            ref.update(updates)
        else:
            ref.set({
                "employee_id": emp_id,
                "date":        date_str,
                "in_time":     time_str if action == "IN" else "—",
                "out_time":    "—",
                "duty_status": "absent",
                "ot_status":   "none",
                "duty_hours":  0,
                "manual":      False,
                "created_at":  datetime.now().isoformat(),
            })

    def _manual_mark(self, force: str = None):
        emp_id = self.manual_var.get().strip().upper()
        if not emp_id:
            self.manual_status.config(
                text="❌ Enter Employee ID first.", fg="#e74c3c")
            return
        if force:
            # Directly write forced action
            name = self._emp_cache.get(emp_id, "")
            if not name:
                try:
                    doc = self.db.collection("employees").document(emp_id).get()
                    if doc.exists:
                        name = doc.to_dict().get("name", "")
                    else:
                        self.manual_status.config(
                            text=f"❌ '{emp_id}' not found.", fg="#e74c3c")
                        return
                except Exception as ex:
                    self.manual_status.config(text=str(ex), fg="#e74c3c"); return
            ts = datetime.now().isoformat()
            try:
                self.db.collection("attendance_logs").add({
                    "employee_id": emp_id,
                    "timestamp":   ts,
                    "action":      force,
                    "session":     1,
                    "location":    "Security Gate (Manual)",
                    "method":      "MANUAL_FORCE",
                    "scanned_by":  self.current_user.get("username", "security"),
                })
                self._update_session(emp_id, _today(), force, _now_str())
            except Exception as ex:
                self._save_local_log(emp_id, name, force, _today(), _now_str(), "MANUAL_FORCE")
            colour = "#00cc66" if force == "IN" else "#ff6644"
            self.manual_status.config(
                text=f"✔ {emp_id} — Force {force} at {_now_str()}", fg=colour)
            self.log_tree.insert("", 0,
                values=(_now_str(), emp_id, name, force, "MANUAL_FORCE"),
                tags=("in" if force == "IN" else "out",))
            self.manual_var.set("")
        else:
            self._process_scan(emp_id, "MANUAL")

    def _load_today_log(self):
        self.log_tree.delete(*self.log_tree.get_children())
        tod = _today()
        count = 0
        try:
            docs = self.db.collection("attendance_logs") \
                .where("timestamp", ">=", tod + "T00:00:00") \
                .order_by("timestamp", direction="DESCENDING") \
                .limit(500).stream()
            for doc in docs:
                lg     = doc.to_dict()
                ts     = str(lg.get("timestamp", ""))
                emp_id = lg.get("employee_id", "")
                name   = self._emp_cache.get(emp_id, "")
                action = lg.get("action", "")
                method = lg.get("method", "APP")
                self.log_tree.insert("", "end",
                    values=(ts[11:19], emp_id, name, action, method),
                    tags=("in" if action == "IN" else "out",))
                count += 1
            self.log_count_lbl.config(
                text=f"Today’s scans: {count}  |  {tod}")
        except Exception as e:
            self.log_count_lbl.config(text=f"Error loading logs: {e}")

    def _save_local_log(self, emp_id, name, action, date_str, time_str, method):
        file_exists = os.path.exists(LOG_FILE)
        with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if not file_exists:
                w.writerow(["date", "time", "employee_id", "name", "action", "method"])
            w.writerow([date_str, time_str, emp_id, name, action, method])
