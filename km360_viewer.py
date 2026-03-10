#!/usr/bin/env python3
"""
KeyMission 360 Viewer
=====================

Interactive 360° photo and video viewer for equirectangular content.

Supports:
- 360° photos (equirectangular JPEG)
- 360° videos (equirectangular MP4)
- Mouse drag to look around
- Scroll to zoom
- Keyboard controls (arrow keys, WASD)

Projection:
    Converts equirectangular projection to rectilinear (perspective)
    for interactive viewing.

Usage:
    python3 km360_viewer.py photo.jpg
    python3 km360_viewer.py video.mp4
    python3 km360_viewer.py --headless  # Test mode

Controls:
    Mouse Drag  - Look around (change yaw/pitch)
    Scroll      - Zoom in/out (change field of view)
    Arrow Keys  - Look around
    WASD        - Look around
    +/-         - Zoom
    Space       - Play/pause (video)
    F           - Toggle fullscreen
    R           - Reset view
    Q/Esc       - Quit

Author: KeyMission 360 Tools Project
License: MIT
"""

import argparse
import sys
import math
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, filedialog

# Optional video support
try:
    import cv2
    VIDEO_SUPPORT = True
except ImportError:
    VIDEO_SUPPORT = False


class EquirectangularProjector:
    """
    Projects equirectangular images/videos to rectilinear (perspective) view.
    
    Equirectangular format:
        - X axis = yaw (longitude) 0-360°
        - Y axis = pitch (latitude) -90 to +90°
    
    Rectilinear projection:
        - Straight lines remain straight
        - Natural perspective view
        - Limited field of view (FOV)
    """
    
    def __init__(self, width=800, height=600, fov=90):
        self.width = width
        self.height = height
        self.fov = math.radians(fov)  # Field of view in radians
        self.yaw = 0  # Horizontal rotation (-π to π)
        self.pitch = 0  # Vertical rotation (-π/2 to π/2)
        
    def set_view(self, yaw, pitch):
        """Set viewing direction"""
        self.yaw = yaw
        self.pitch = pitch
        
        # Clamp pitch to avoid gimbal lock
        self.pitch = max(-math.pi/2 + 0.01, min(math.pi/2 - 0.01, self.pitch))
        
    def rotate(self, delta_yaw, delta_pitch):
        """Rotate view by delta"""
        self.yaw += delta_yaw
        self.pitch += delta_pitch
        self.pitch = max(-math.pi/2 + 0.01, min(math.pi/2 - 0.01, self.pitch))
        
    def zoom(self, factor):
        """Zoom by changing FOV"""
        self.fov *= factor
        self.fov = max(math.radians(30), min(math.radians(120), self.fov))
        
    def project(self, eq_img):
        """
        Project equirectangular image to rectilinear view.
        
        Args:
            eq_img: PIL Image or numpy array (H, W, 3) in equirectangular format
            
        Returns:
            PIL Image of projected view
        """
        if isinstance(eq_img, Image.Image):
            eq_array = np.array(eq_img)
        else:
            eq_array = eq_img
            
        eq_h, eq_w = eq_array.shape[:2]
        
        # Create output image
        out = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Calculate projection parameters
        f = (self.width / 2) / math.tan(self.fov / 2)
        
        # Center of output image
        cx, cy = self.width / 2, self.height / 2
        
        # Rotation matrix for yaw and pitch
        cos_yaw, sin_yaw = math.cos(self.yaw), math.sin(self.yaw)
        cos_pitch, sin_pitch = math.cos(self.pitch), math.sin(self.pitch)
        
        # Generate pixel coordinates
        x_coords = np.arange(self.width) - cx
        y_coords = np.arange(self.height) - cy
        xv, yv = np.meshgrid(x_coords, y_coords)
        
        # Convert to 3D direction vectors
        z = np.full_like(xv, f, dtype=np.float32)
        x = xv.astype(np.float32)
        y = yv.astype(np.float32)
        
        # Normalize
        norm = np.sqrt(x*x + y*y + z*z)
        x, y, z = x/norm, y/norm, z/norm
        
        # Apply pitch rotation (around X axis)
        y_rot = y * cos_pitch - z * sin_pitch
        z_rot = y * sin_pitch + z * cos_pitch
        y, z = y_rot, z_rot
        
        # Apply yaw rotation (around Y axis)
        x_rot = x * cos_yaw - z * sin_yaw
        z_rot = x * sin_yaw + z * cos_yaw
        x, z = x_rot, z_rot
        
        # Convert to spherical coordinates
        theta = np.arctan2(x, z)  # -pi to pi
        phi = np.arcsin(y)        # -pi/2 to pi/2
        
        # Map to equirectangular coordinates
        eq_x = ((theta / math.pi + 1) / 2 * (eq_w - 1)).astype(np.int32)
        eq_y = ((-phi / (math.pi/2) + 1) / 2 * (eq_h - 1)).astype(np.int32)
        
        # Clamp coordinates
        eq_x = np.clip(eq_x, 0, eq_w - 1)
        eq_y = np.clip(eq_y, 0, eq_h - 1)
        
        # Sample from equirectangular image
        out = eq_array[eq_y, eq_x]
        
        return Image.fromarray(out)


class Viewer360:
    """Interactive 360° image/video viewer"""
    
    def __init__(self, root, file_path=None):
        self.root = root
        self.root.title("KeyMission 360 Viewer")
        self.root.geometry("1000x700")
        
        # State
        self.file_path = file_path
        self.is_video = False
        self.video_capture = None
        self.current_frame = None
        self.playing = False
        self.projector = EquirectangularProjector(width=800, height=600)
        
        # Mouse state
        self.dragging = False
        self.last_x = 0
        self.last_y = 0
        self.sensitivity = 0.005
        
        # Setup UI
        self.setup_ui()
        
        # Load file if provided
        if file_path:
            self.load_file(file_path)
        
        # Bind controls
        self.bind_controls()
        
        # Start update loop
        self.update()
    
    def setup_ui(self):
        """Setup user interface"""
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Canvas for image display
        self.canvas = tk.Canvas(main_frame, width=800, height=600, bg='black')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Controls frame
        controls = ttk.Frame(main_frame)
        controls.pack(fill=tk.X, pady=5)
        
        # File button
        ttk.Button(controls, text="Open File", command=self.open_file).pack(side=tk.LEFT, padx=5)
        
        # Video controls (if video)
        self.play_btn = ttk.Button(controls, text="Play", command=self.toggle_play)
        self.play_btn.pack(side=tk.LEFT, padx=5)
        self.play_btn.config(state=tk.DISABLED)
        
        # Reset button
        ttk.Button(controls, text="Reset View", command=self.reset_view).pack(side=tk.LEFT, padx=5)
        
        # Info label
        self.info_label = ttk.Label(controls, text="No file loaded")
        self.info_label.pack(side=tk.RIGHT, padx=5)
        
        # Status bar with controls help
        status = ttk.Label(self.root, text="Drag to look • Scroll to zoom • Arrows/WASD to look • +/- to zoom • R to reset • Q to quit",
                          relief=tk.SUNKEN, anchor=tk.W)
        status.pack(side=tk.BOTTOM, fill=tk.X)
    
    def bind_controls(self):
        """Bind mouse and keyboard controls"""
        # Mouse controls
        self.canvas.bind("<Button-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<MouseWheel>", self.on_scroll)  # Windows/Mac
        self.canvas.bind("<Button-4>", self.on_scroll)    # Linux scroll up
        self.canvas.bind("<Button-5>", self.on_scroll)    # Linux scroll down
        
        # Keyboard controls
        self.root.bind("<Left>", lambda e: self.rotate(-0.1, 0))
        self.root.bind("<Right>", lambda e: self.rotate(0.1, 0))
        self.root.bind("<Up>", lambda e: self.rotate(0, 0.1))
        self.root.bind("<Down>", lambda e: self.rotate(0, -0.1))
        self.root.bind("<a>", lambda e: self.rotate(-0.1, 0))
        self.root.bind("<d>", lambda e: self.rotate(0.1, 0))
        self.root.bind("<w>", lambda e: self.rotate(0, 0.1))
        self.root.bind("<s>", lambda e: self.rotate(0, -0.1))
        self.root.bind("<plus>", lambda e: self.zoom(0.9))
        self.root.bind("<minus>", lambda e: self.zoom(1.1))
        self.root.bind("<r>", lambda e: self.reset_view())
        self.root.bind("<R>", lambda e: self.reset_view())
        self.root.bind("<q>", lambda e: self.root.quit())
        self.root.bind("<Q>", lambda e: self.root.quit())
        self.root.bind("<Escape>", lambda e: self.root.quit())
        self.root.bind("<space>", lambda e: self.toggle_play())
        self.root.bind("<f>", lambda e: self.toggle_fullscreen())
        self.root.bind("<F>", lambda e: self.toggle_fullscreen())
    
    def load_file(self, path):
        """Load an image or video file"""
        self.file_path = path
        ext = path.lower().split('.')[-1]
        
        if ext in ['mp4', 'mov', 'avi']:
            self.load_video(path)
        else:
            self.load_image(path)
    
    def load_image(self, path):
        """Load a 360° image"""
        try:
            self.current_frame = Image.open(path)
            self.is_video = False
            self.info_label.config(text=f"Image: {self.current_frame.size[0]}x{self.current_frame.size[1]}")
            self.play_btn.config(state=tk.DISABLED)
            self.render()
        except Exception as e:
            print(f"Error loading image: {e}")
    
    def load_video(self, path):
        """Load a 360° video"""
        if not VIDEO_SUPPORT:
            print("Video support not available. Install opencv-python: pip install opencv-python")
            return
        
        try:
            if self.video_capture:
                self.video_capture.release()
            
            self.video_capture = cv2.VideoCapture(path)
            self.is_video = True
            self.playing = True
            
            width = int(self.video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self.video_capture.get(cv2.CAP_PROP_FPS)
            
            self.info_label.config(text=f"Video: {width}x{height} @ {fps:.1f}fps")
            self.play_btn.config(state=tk.NORMAL, text="Pause")
            
            # Read first frame
            ret, frame = self.video_capture.read()
            if ret:
                self.current_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.render()
                
        except Exception as e:
            print(f"Error loading video: {e}")
    
    def open_file(self):
        """Open file dialog"""
        path = filedialog.askopenfilename(
            title="Open 360° Image or Video",
            filetypes=[
                ("360° Media", "*.jpg *.jpeg *.png *.mp4 *.mov *.avi"),
                ("Images", "*.jpg *.jpeg *.png"),
                ("Videos", "*.mp4 *.mov *.avi"),
                ("All Files", "*.*")
            ]
        )
        if path:
            self.load_file(path)
    
    def render(self):
        """Render current view"""
        if self.current_frame is None:
            return
        
        # Project to rectilinear view
        projected = self.projector.project(self.current_frame)
        
        # Convert to PhotoImage
        self.tk_image = ImageTk.PhotoImage(projected)
        
        # Update canvas
        self.canvas.delete("all")
        self.canvas.create_image(
            self.canvas.winfo_width() // 2,
            self.canvas.winfo_height() // 2,
            image=self.tk_image
        )
    
    def update(self):
        """Update loop for video playback"""
        if self.is_video and self.playing and self.video_capture:
            ret, frame = self.video_capture.read()
            if ret:
                self.current_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.render()
            else:
                # Loop video
                self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        self.root.after(33, self.update)  # ~30fps
    
    # Control methods
    def on_mouse_down(self, event):
        self.dragging = True
        self.last_x = event.x
        self.last_y = event.y
    
    def on_mouse_drag(self, event):
        if not self.dragging:
            return
        
        dx = event.x - self.last_x
        dy = event.y - self.last_y
        
        self.rotate(dx * self.sensitivity, -dy * self.sensitivity)
        
        self.last_x = event.x
        self.last_y = event.y
    
    def on_mouse_up(self, event):
        self.dragging = False
    
    def on_mouse_move(self, event):
        pass  # Could show coordinates here
    
    def on_scroll(self, event):
        """Handle mouse wheel zoom"""
        if event.num == 4 or event.delta > 0:  # Scroll up
            self.zoom(0.9)
        elif event.num == 5 or event.delta < 0:  # Scroll down
            self.zoom(1.1)
    
    def rotate(self, yaw_delta, pitch_delta):
        """Rotate view"""
        self.projector.rotate(yaw_delta, pitch_delta)
        self.render()
    
    def zoom(self, factor):
        """Zoom view"""
        self.projector.zoom(factor)
        self.render()
    
    def reset_view(self):
        """Reset to default view"""
        self.projector.yaw = 0
        self.projector.pitch = 0
        self.projector.fov = math.radians(90)
        self.render()
    
    def toggle_play(self):
        """Toggle video playback"""
        if not self.is_video:
            return
        self.playing = not self.playing
        self.play_btn.config(text="Pause" if self.playing else "Play")
    
    def toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        is_fullscreen = self.root.attributes("-fullscreen")
        self.root.attributes("-fullscreen", not is_fullscreen)


def run_headless_test():
    """Run tests without GUI"""
    print("=" * 60)
    print("KeyMission 360 Viewer - Headless Test Mode")
    print("=" * 60)
    print()
    
    # Test 1: Check imports
    print("[TEST 1] Checking Python imports...")
    try:
        import numpy as np
        from PIL import Image
        print("  ✓ numpy imported")
        print("  ✓ PIL imported")
    except ImportError as e:
        print(f"  ✗ Import error: {e}")
        return
    
    # Test 2: Check video support
    print("\n[TEST 2] Checking video support...")
    if VIDEO_SUPPORT:
        import cv2
        print(f"  ✓ OpenCV available: {cv2.__version__}")
    else:
        print("  ⚠ OpenCV not available (pip install opencv-python)")
    
    # Test 3: Test projection math
    print("\n[TEST 3] Testing projection...")
    try:
        projector = EquirectangularProjector(width=400, height=300)
        
        # Create dummy equirectangular image
        eq_img = np.random.randint(0, 255, (512, 1024, 3), dtype=np.uint8)
        
        # Project
        result = projector.project(eq_img)
        print(f"  ✓ Projection works: {result.size}")
        
        # Test rotation
        projector.rotate(0.5, 0.3)
        result2 = projector.project(eq_img)
        print(f"  ✓ Rotation works: yaw={projector.yaw:.2f}, pitch={projector.pitch:.2f}")
        
        # Test zoom
        projector.zoom(0.8)
        print(f"  ✓ Zoom works: fov={math.degrees(projector.fov):.1f}°")
        
    except Exception as e:
        print(f"  ✗ Projection error: {e}")
    
    print("\n" + "=" * 60)
    print("Headless test complete")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Interactive 360° photo and video viewer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Open viewer (use File menu)
  %(prog)s photo.jpg          # Open image directly
  %(prog)s video.mp4          # Open video directly
  %(prog)s --headless         # Run tests

Controls:
  Mouse Drag  - Look around
  Scroll      - Zoom in/out
  Arrow/WASD  - Look around
  +/-         - Zoom
  Space       - Play/Pause (video)
  F           - Fullscreen
  R           - Reset view
  Q/Esc       - Quit
"""
    )
    
    parser.add_argument("file", nargs="?", help="Image or video file to open")
    parser.add_argument("--headless", "--test", "-t", action="store_true",
                       help="Run headless tests")
    parser.add_argument("--width", "-w", type=int, default=800, help="Viewport width")
    parser.add_argument("--height", "-H", type=int, default=600, help="Viewport height")
    
    args = parser.parse_args()
    
    # Headless test mode
    if args.headless:
        run_headless_test()
        sys.exit(0)
    
    # GUI mode
    root = tk.Tk()
    
    if args.file:
        app = Viewer360(root, args.file)
    else:
        app = Viewer360(root)
    
    root.mainloop()


if __name__ == "__main__":
    main()
