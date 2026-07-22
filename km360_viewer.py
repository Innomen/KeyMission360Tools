#!/usr/bin/env python3
"""Interactive spherical viewer and non-destructive panorama leveler."""

from __future__ import annotations
import argparse
import math
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import numpy as np
from PIL import Image, ImageTk

try:
    import cv2
except ImportError:
    cv2 = None

BG, PANEL, PANEL2, TEXT, MUTED, ACCENT = (
    "#11151c",
    "#1a202b",
    "#222a37",
    "#edf2f7",
    "#9aa7b8",
    "#57c7ff",
)


def rotation_matrix(yaw=0.0, pitch=0.0, roll=0.0):
    cy, sy, cp, sp, cr, sr = (
        math.cos(yaw),
        math.sin(yaw),
        math.cos(pitch),
        math.sin(pitch),
        math.cos(roll),
        math.sin(roll),
    )
    return (
        np.array(((cy, 0, -sy), (0, 1, 0), (sy, 0, cy)))
        @ np.array(((1, 0, 0), (0, cp, -sp), (0, sp, cp)))
        @ np.array(((cr, -sr, 0), (sr, cr, 0), (0, 0, 1)))
    )


def remap(source, map_x, map_y, quality=cv2.INTER_LINEAR if cv2 else None):
    if cv2 is not None:
        return cv2.remap(
            source,
            map_x.astype(np.float32),
            map_y.astype(np.float32),
            quality,
            borderMode=cv2.BORDER_WRAP,
        )
    return source[
        np.clip(map_y.astype(int), 0, source.shape[0] - 1),
        np.mod(map_x.astype(int), source.shape[1]),
    ]


class Projector:
    def __init__(self, width=960, height=600):
        self.width, self.height, self.yaw, self.pitch, self.roll, self.fov = (
            width,
            height,
            0.0,
            0.0,
            0.0,
            math.radians(90),
        )

    def project(self, image):
        src = np.asarray(image.convert("RGB"))
        h, w = src.shape[:2]
        f = (self.width / 2) / math.tan(self.fov / 2)
        x, y = np.meshgrid(
            np.arange(self.width) - self.width / 2,
            np.arange(self.height) - self.height / 2,
        )
        rays = np.stack((x, y, np.full_like(x, f)), axis=-1).astype(np.float32)
        rays /= np.linalg.norm(rays, axis=-1, keepdims=True)
        rays = rays @ rotation_matrix(self.yaw, self.pitch, self.roll).T
        lon = np.arctan2(rays[..., 0], rays[..., 2])
        lat = np.arcsin(np.clip(rays[..., 1], -1, 1))
        return Image.fromarray(
            remap(src, (lon / (2 * math.pi) + 0.5) * w, (0.5 - lat / math.pi) * (h - 1))
        )


def reorient_equirectangular(image, yaw, pitch, roll):
    src = np.asarray(image.convert("RGB"))
    h, w = src.shape[:2]
    lon, lat = np.meshgrid(
        (np.arange(w) / w - 0.5) * 2 * math.pi, (0.5 - np.arange(h) / (h - 1)) * math.pi
    )
    vec = np.stack(
        (np.cos(lat) * np.sin(lon), np.sin(lat), np.cos(lat) * np.cos(lon)), axis=-1
    ) @ rotation_matrix(yaw, pitch, roll)
    slon = np.arctan2(vec[..., 0], vec[..., 2])
    slat = np.arcsin(np.clip(vec[..., 1], -1, 1))
    return Image.fromarray(
        remap(
            src,
            (slon / (2 * math.pi) + 0.5) * w,
            (0.5 - slat / math.pi) * (h - 1),
            cv2.INTER_CUBIC if cv2 else None,
        )
    )


class Viewer360:
    def __init__(self, parent, file_path=None):
        self.window = tk.Toplevel(parent) if parent else tk.Tk()
        self.window.title("KeyMission 360 • Sphere Viewer")
        self.window.geometry("1200x820")
        self.window.minsize(840, 620)
        self.window.configure(bg=BG)
        self.file_path = self.frame = self.capture = self.drag = None
        self.playing = False
        self.projector = Projector()
        self._style()
        self._build()
        self._bind()
        self.window.after(33, self._tick)
        if file_path:
            self.load(file_path)
        else:
            self.open_file()

    def _style(self):
        s = ttk.Style(self.window)
        s.theme_use("clam")
        s.configure("Viewer.TFrame", background=BG)
        s.configure("Viewer.TLabel", background=BG, foreground=TEXT)
        s.configure("ViewerMuted.TLabel", background=BG, foreground=MUTED)
        s.configure(
            "Viewer.TButton", background=PANEL2, foreground=TEXT, padding=(12, 8)
        )
        s.configure(
            "ViewerAccent.TButton",
            background=ACCENT,
            foreground="#071018",
            padding=(12, 8),
        )

    def _build(self):
        bar = ttk.Frame(self.window, style="Viewer.TFrame", padding=(18, 14))
        bar.pack(fill="x")
        ttk.Label(
            bar, text="Sphere Viewer", style="Viewer.TLabel", font=("Sans", 18, "bold")
        ).pack(side="left")
        ttk.Button(
            bar, text="Open media", style="ViewerAccent.TButton", command=self.open_file
        ).pack(side="left", padx=14)
        ttk.Button(
            bar, text="Reset view", style="Viewer.TButton", command=self.reset_view
        ).pack(side="left")
        self.save_btn = ttk.Button(
            bar,
            text="Export leveled copy",
            style="Viewer.TButton",
            command=self.export_copy,
            state="disabled",
        )
        self.save_btn.pack(side="right")
        self.canvas = tk.Canvas(self.window, bg="#06080b", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=18)
        self.canvas.bind("<Configure>", self._resize)
        controls = ttk.Frame(
            self.window, style="Viewer.TFrame", padding=(18, 12, 18, 16)
        )
        controls.pack(fill="x")
        ttk.Label(controls, text="Roll", style="Viewer.TLabel").pack(side="left")
        self.roll_var = tk.DoubleVar(value=0)
        ttk.Scale(
            controls,
            from_=-180,
            to=180,
            variable=self.roll_var,
            command=self._roll,
            length=260,
        ).pack(side="left", padx=8)
        self.roll_label = ttk.Label(
            controls, text="0.0°", style="ViewerMuted.TLabel", width=8
        )
        self.roll_label.pack(side="left")
        for text, delta in (("−90°", -90), ("+90°", 90)):
            ttk.Button(
                controls,
                text=text,
                style="Viewer.TButton",
                command=lambda d=delta: self.set_roll(self.roll_var.get() + d),
            ).pack(side="left", padx=3)
        self.guide = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            controls, text="Horizon guide", variable=self.guide, command=self.render
        ).pack(side="left", padx=14)
        self.info = ttk.Label(
            controls,
            text="Drag to look • wheel to zoom • level with Roll",
            style="ViewerMuted.TLabel",
        )
        self.info.pack(side="right")

    def _bind(self):
        self.canvas.bind("<Button-1>", lambda e: setattr(self, "drag", (e.x, e.y)))
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", lambda e: setattr(self, "drag", None))
        self.canvas.bind("<Button-4>", lambda e: self.zoom(0.9))
        self.canvas.bind("<Button-5>", lambda e: self.zoom(1.1))
        self.window.bind("<Escape>", lambda e: self.window.destroy())

    def open_file(self):
        p = filedialog.askopenfilename(
            parent=self.window,
            title="Open 360 media",
            filetypes=(
                ("360 media", "*.jpg *.jpeg *.png *.mp4 *.mov *.avi"),
                ("Images", "*.jpg *.jpeg *.png"),
                ("Videos", "*.mp4 *.mov *.avi"),
            ),
        )
        if p:
            self.load(p)

    def load(self, path):
        self.file_path = Path(path)
        if self.capture:
            self.capture.release()
            self.capture = None
        if self.file_path.suffix.lower() in (".mp4", ".mov", ".avi"):
            if cv2 is None:
                return messagebox.showerror(
                    "Sphere Viewer",
                    "Video support requires OpenCV.",
                    parent=self.window,
                )
            self.capture = cv2.VideoCapture(str(self.file_path))
            ok, frame = self.capture.read()
            if not ok:
                return messagebox.showerror(
                    "Sphere Viewer",
                    "The video could not be opened.",
                    parent=self.window,
                )
            self.frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            self.playing = True
            self.save_btn.config(state="disabled")
        else:
            self.frame = Image.open(self.file_path).convert("RGB")
            self.playing = False
            self.save_btn.config(state="normal")
        self.reset_view()
        self.info.config(text=f"{self.file_path.name} • drag • zoom • level with Roll")

    def _resize(self, e):
        self.projector.width = max(320, e.width)
        self.projector.height = max(240, e.height)
        self.render()

    def _drag(self, e):
        if not self.drag:
            return
        x, y = self.drag
        self.projector.yaw += (e.x - x) * 0.004
        self.projector.pitch = float(
            np.clip(
                self.projector.pitch - (e.y - y) * 0.004,
                -math.pi / 2 + 0.01,
                math.pi / 2 - 0.01,
            )
        )
        self.drag = (e.x, e.y)
        self.render()

    def zoom(self, f):
        self.projector.fov = float(
            np.clip(self.projector.fov * f, math.radians(25), math.radians(120))
        )
        self.render()

    def _roll(self, v):
        self.projector.roll = math.radians(float(v))
        self.roll_label.config(text=f"{float(v):.1f}°")
        self.render()

    def set_roll(self, v):
        v = ((v + 180) % 360) - 180
        self.roll_var.set(v)
        self._roll(v)

    def reset_view(self):
        self.projector.yaw = self.projector.pitch = self.projector.roll = 0
        self.projector.fov = math.radians(90)
        self.roll_var.set(0)
        self.roll_label.config(text="0.0°")
        self.render()

    def render(self):
        if self.frame is None or self.canvas.winfo_width() < 2:
            return
        self.tk_image = ImageTk.PhotoImage(self.projector.project(self.frame))
        self.canvas.delete("all")
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        self.canvas.create_image(w / 2, h / 2, image=self.tk_image)
        if self.guide.get():
            self.canvas.create_line(
                0, h / 2, w, h / 2, fill=ACCENT, dash=(8, 8), width=2
            )
            self.canvas.create_line(
                w / 2, h / 2 - 28, w / 2, h / 2 + 28, fill=ACCENT, width=2
            )

    def export_copy(self):
        default = self.file_path.with_name(self.file_path.stem + "_leveled.jpg")
        p = filedialog.asksaveasfilename(
            parent=self.window,
            title="Export leveled panorama",
            initialdir=str(default.parent),
            initialfile=default.name,
            defaultextension=".jpg",
            filetypes=(("JPEG", "*.jpg"), ("PNG", "*.png")),
        )
        if p:
            reorient_equirectangular(
                self.frame,
                self.projector.yaw,
                self.projector.pitch,
                self.projector.roll,
            ).save(p, quality=95)
            messagebox.showinfo(
                "Sphere Viewer",
                "Leveled copy exported. The original was not changed.",
                parent=self.window,
            )

    def _tick(self):
        if self.capture and self.playing:
            ok, frame = self.capture.read()
            if ok:
                self.frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                self.render()
            else:
                self.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
        if self.window.winfo_exists():
            self.window.after(33, self._tick)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("file", nargs="?")
    p.add_argument("--test", "--headless", action="store_true")
    a = p.parse_args()
    if a.test:
        fixture = Image.new("RGB", (1024, 512), "navy")
        assert Projector(320, 200).project(fixture).size == (320, 200)
        assert reorient_equirectangular(fixture, 0, 0, math.pi / 2).size == fixture.size
        print("✓ spherical projection and reorientation passed")
        return 0
    root = tk.Tk()
    root.withdraw()
    Viewer360(root, a.file)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
