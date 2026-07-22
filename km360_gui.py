#!/usr/bin/env python3
"""KeyMission 360 desktop control center."""

from __future__ import annotations

import queue
import subprocess
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

from km360_config import ask_directory, get_last_download_dir, set_last_download_dir
from km360_core import Camera, CameraFile, dependency_status
from km360_sphere_viewer import launch_viewer

BG = "#11151c"
PANEL = "#1a202b"
PANEL_2 = "#222a37"
TEXT = "#edf2f7"
MUTED = "#9aa7b8"
ACCENT = "#57c7ff"
GOOD = "#54d69b"
WARN = "#ffca66"
BAD = "#ff6b7a"


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.camera = Camera()
        self.items: list[CameraFile] = []
        self.events: queue.Queue = queue.Queue()
        self.busy = False
        self.destination = Path(get_last_download_dir())
        self._style()
        self._build()
        self.root.after(80, self._drain)
        self.refresh()

    def _style(self):
        self.root.title("KeyMission 360")
        self.root.geometry("1120x820")
        self.root.minsize(860, 700)
        self.root.configure(bg=BG)
        s = ttk.Style()
        s.theme_use("clam")
        s.configure(
            ".", background=BG, foreground=TEXT, fieldbackground=PANEL, borderwidth=0
        )
        s.configure("TFrame", background=BG)
        s.configure("Panel.TFrame", background=PANEL)
        s.configure(
            "Title.TLabel", background=BG, foreground=TEXT, font=("Sans", 24, "bold")
        )
        s.configure("Sub.TLabel", background=BG, foreground=MUTED, font=("Sans", 10))
        s.configure("Card.TLabel", background=PANEL, foreground=TEXT)
        s.configure(
            "Status.TLabel", background=PANEL, foreground=MUTED, font=("Sans", 11)
        )
        s.configure(
            "Accent.TButton",
            background=ACCENT,
            foreground="#071018",
            padding=(18, 11),
            font=("Sans", 10, "bold"),
        )
        s.map("Accent.TButton", background=[("active", "#86d8ff")])
        s.configure("TButton", background=PANEL_2, foreground=TEXT, padding=(14, 9))
        s.map("TButton", background=[("active", "#303b4d")])
        s.configure(
            "Treeview",
            background=PANEL,
            fieldbackground=PANEL,
            foreground=TEXT,
            rowheight=32,
        )
        s.configure("Treeview.Heading", background=PANEL_2, foreground=TEXT, padding=8)
        s.map("Treeview", background=[("selected", "#244a63")])

    def _build(self):
        top = ttk.Frame(self.root, padding=(24, 20, 24, 12))
        top.pack(fill="x")
        ttk.Label(top, text="KeyMission 360", style="Title.TLabel").pack(side="left")
        ttk.Label(top, text="CAMERA CONTROL + MEDIA OFFLOAD", style="Sub.TLabel").pack(
            side="left", padx=18, pady=(12, 0)
        )
        self.refresh_btn = ttk.Button(top, text="Refresh", command=self.refresh)
        self.refresh_btn.pack(side="right")

        status = ttk.Frame(self.root, style="Panel.TFrame", padding=18)
        status.pack(fill="x", padx=24, pady=(0, 14))
        self.dot = tk.Canvas(
            status, width=14, height=14, bg=PANEL, highlightthickness=0
        )
        self.dot.pack(side="left")
        self.dot_id = self.dot.create_oval(2, 2, 12, 12, fill=MUTED, outline="")
        self.status = ttk.Label(status, text="Checking camera…", style="Status.TLabel")
        self.status.pack(side="left", padx=10)
        self.summary = ttk.Label(status, text="", style="Status.TLabel")
        self.summary.pack(side="right")

        body = ttk.PanedWindow(self.root, orient="horizontal")
        body.pack(fill="both", expand=True, padx=24, pady=(0, 14))
        library = ttk.Frame(body, style="Panel.TFrame", padding=14)
        actions = ttk.Frame(body, style="Panel.TFrame", padding=18)
        body.add(library, weight=3)
        body.add(actions, weight=1)

        ttk.Label(
            library,
            text="Media on camera",
            style="Card.TLabel",
            font=("Sans", 12, "bold"),
        ).pack(anchor="w", pady=(0, 10))
        self.tree = ttk.Treeview(
            library,
            columns=("kind", "size", "date"),
            show="tree headings",
            selectmode="extended",
        )
        self.tree.heading("#0", text="File")
        self.tree.heading("kind", text="Type")
        self.tree.heading("size", text="Size")
        self.tree.heading("date", text="Captured")
        self.tree.column("#0", width=280)
        self.tree.column("kind", width=90, anchor="center")
        self.tree.column("size", width=90, anchor="e")
        self.tree.column("date", width=140, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self._open_tree_item)
        self.tree.bind("<Return>", self._open_tree_item)
        self.tree.bind("<Button-3>", self._show_media_menu)
        self.tree.bind("<<TreeviewSelect>>", self._media_selected)
        self.media_menu = tk.Menu(
            self.root,
            tearoff=False,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#303b4d",
            activeforeground=TEXT,
        )
        self.media_menu.add_command(
            label="View in sphere viewer", command=self.view_selected
        )
        self.media_menu.add_command(
            label="Download this item", command=self.download_selected
        )

        ttk.Label(
            actions, text="Offload", style="Card.TLabel", font=("Sans", 13, "bold")
        ).pack(anchor="w")
        ttk.Label(
            actions,
            text="Download first. Delete only after every object is accounted for.",
            style="Status.TLabel",
            wraplength=260,
        ).pack(anchor="w", pady=(4, 14))
        self.dest_label = ttk.Label(
            actions, text=self._short_dest(), style="Status.TLabel", wraplength=260
        )
        self.dest_label.pack(anchor="w", pady=(0, 8))
        self.view_btn = ttk.Button(
            actions,
            text="View selected media",
            style="Accent.TButton",
            command=self.view_selected,
        )
        self.view_btn.pack(fill="x", pady=(0, 8))
        ttk.Button(
            actions, text="Choose destination", command=self.choose_destination
        ).pack(fill="x", pady=3)
        self.download_btn = ttk.Button(
            actions,
            text="Download all safely",
            style="Accent.TButton",
            command=self.download_all,
        )
        self.download_btn.pack(fill="x", pady=(8, 3))
        self.delete_btn = ttk.Button(
            actions, text="Erase camera media…", command=self.delete_all
        )
        self.delete_btn.pack(fill="x", pady=3)

        ttk.Separator(actions).pack(fill="x", pady=18)
        ttk.Label(
            actions, text="Camera", style="Card.TLabel", font=("Sans", 13, "bold")
        ).pack(anchor="w", pady=(0, 8))
        ttk.Button(actions, text="Sync camera clock", command=self.sync_time).pack(
            fill="x", pady=3
        )
        ttk.Button(
            actions, text="Open 360 photo or video", command=self.open_viewer
        ).pack(fill="x", pady=3)
        ttk.Button(
            actions,
            text="Camera settings",
            command=lambda: self._launch_cli("settings", "--show"),
        ).pack(fill="x", pady=3)
        ttk.Button(
            actions, text="Connection diagnostics", command=self.diagnostics
        ).pack(fill="x", pady=3)

        self.progress = ttk.Progressbar(self.root, mode="determinate")
        self.progress.pack(fill="x", padx=24)
        self.activity = ttk.Label(
            self.root, text="Ready", style="Sub.TLabel", padding=(0, 2)
        )
        self.activity.pack(fill="x", padx=24, pady=(8, 18))

    def _short_dest(self):
        return f"Destination: {self.destination.name or self.destination}"

    def _work(self, fn, done=None):
        if self.busy:
            return
        self.busy = True
        self._controls(False)

        def run():
            try:
                value = fn()
                self.events.put(("done", value, done))
            except Exception as exc:
                self.events.put(("error", str(exc), None))

        threading.Thread(target=run, daemon=True).start()

    def _drain(self):
        try:
            while True:
                kind, value, callback = self.events.get_nowait()
                if kind == "progress":
                    current, total, label = value
                    self.progress["maximum"] = max(total, 1)
                    self.progress["value"] = current
                    self.activity.config(text=label)
                elif kind == "done":
                    self.busy = False
                    self._controls(True)
                    if callback:
                        callback(value)
                else:
                    self.busy = False
                    self._controls(True)
                    self.activity.config(text="Operation failed")
                    messagebox.showerror("KeyMission 360", value)
        except queue.Empty:
            pass
        self.root.after(80, self._drain)

    def _controls(self, enabled):
        state = "normal" if enabled else "disabled"
        for widget in (
            self.refresh_btn,
            self.view_btn,
            self.download_btn,
            self.delete_btn,
        ):
            widget.config(state=state)

    def refresh(self):
        self.activity.config(text="Reading camera…")
        self._work(self.camera.files, self._show_files)

    def _show_files(self, files):
        supported = (".jpg", ".jpeg", ".png", ".mp4", ".mov", ".avi")
        self.items = [
            item for item in files if Path(item.name).suffix.lower() in supported
        ]
        self.tree.delete(*self.tree.get_children())
        total = sum(item.size_bytes for item in self.items)
        for item in self.items:
            kind = "Video" if item.mime.startswith("video/") else "Photo"
            date = (
                datetime.fromtimestamp(item.timestamp).strftime("%Y-%m-%d %H:%M")
                if item.timestamp
                else "Unknown"
            )
            self.tree.insert(
                "",
                "end",
                iid=str(item.number),
                text=item.name,
                values=(kind, human_size(item.size_bytes), date),
            )
        self.dot.itemconfig(self.dot_id, fill=GOOD)
        self.status.config(text="Camera connected")
        self.summary.config(text=f"{len(self.items)} items  •  {human_size(total)}")
        self.activity.config(
            text="Camera is empty" if not self.items else "Ready to view or offload"
        )
        self.progress["value"] = 0

    def choose_destination(self):
        selected = ask_directory(
            title="Choose KeyMission download folder", initialdir=str(self.destination)
        )
        if selected:
            self.destination = Path(selected)
            set_last_download_dir(self.destination)
            self.dest_label.config(text=self._short_dest())

    def _selected_item(self):
        selected = self.tree.selection()
        if not selected:
            return None
        number = int(selected[0])
        return next((item for item in self.items if item.number == number), None)

    def _open_tree_item(self, _event=None):
        self.view_selected()

    def _media_selected(self, _event=None):
        if self.tree.selection():
            self.activity.config(
                text="Selected • double-click, press Enter, or choose View selected media"
            )

    def _show_media_menu(self, event):
        row = self.tree.identify_row(event.y)
        if not row:
            return
        self.tree.selection_set(row)
        self.tree.focus(row)
        self.media_menu.tk_popup(event.x_root, event.y_root)

    def _local_copy(self, item):
        path = self.destination / item.name
        if path.is_file() and abs(path.stat().st_size - item.size_bytes) <= 1024:
            return path
        return None

    def view_selected(self):
        item = self._selected_item()
        if item is None:
            messagebox.showinfo("KeyMission 360", "Select a photo or video first.")
            return
        local = self._local_copy(item)
        if local:
            launch_viewer(local)
            return
        self.activity.config(text="Downloading selected media before viewing…")
        self._work(
            lambda: self.camera.download(item, self.destination)[0],
            launch_viewer,
        )

    def download_selected(self):
        item = self._selected_item()
        if item is None:
            messagebox.showinfo("KeyMission 360", "Select a photo or video first.")
            return
        self.activity.config(text="Downloading selected media…")
        self._work(
            lambda: self.camera.download(item, self.destination)[0],
            lambda _path: self.activity.config(text="Selected media downloaded"),
        )

    def download_all(self):
        if not self.items:
            messagebox.showinfo(
                "KeyMission 360", "The camera has no media to download."
            )
            return
        items = list(self.items)

        def job():
            results = []
            for index, item in enumerate(items, 1):
                self.events.put(
                    (
                        "progress",
                        (
                            index - 1,
                            len(items),
                            f"Downloading {index} of {len(items)}…",
                        ),
                        None,
                    )
                )
                results.append(self.camera.download(item, self.destination))
            self.events.put(
                ("progress", (len(items), len(items), "Download complete"), None)
            )
            return len(results)

        self._work(
            job,
            lambda count: messagebox.showinfo(
                "Download complete", f"{count} camera items are safely stored locally."
            ),
        )

    def delete_all(self):
        if not self.items:
            messagebox.showinfo("KeyMission 360", "The camera is already empty.")
            return
        count = len(self.items)
        if not messagebox.askyesno(
            "Erase camera media",
            f"Delete all {count} media items from the camera?\n\nUse this after confirming your download. This cannot be undone.",
            icon="warning",
        ):
            return
        self.activity.config(text="Deleting camera media…")
        self._work(
            self.camera.delete_all,
            lambda _: (
                messagebox.showinfo(
                    "Camera cleared",
                    "All media was deleted and the camera reports empty.",
                ),
                self.refresh(),
            ),
        )

    def sync_time(self):
        self._work(
            self.camera.sync_time,
            lambda _: messagebox.showinfo(
                "Clock synchronized", "The camera clock now matches this computer."
            ),
        )

    def diagnostics(self):
        deps = dependency_status()
        text = "\n".join(
            f"{'Ready' if ok else 'Missing'}: {name}" for name, ok in deps.items()
        )
        messagebox.showinfo("Connection diagnostics", text)

    def open_viewer(self):
        launch_viewer()

    def _launch_cli(self, *args):
        subprocess.Popen(
            [sys.executable, str(Path(__file__).with_name("km360")), *args]
        )


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def main() -> int:
    if "--test" in sys.argv:
        print("✓ GUI imports passed")
        return 0
    root = tk.Tk()
    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
