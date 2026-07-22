#!/usr/bin/env python3
"""GPU-accelerated standalone 360 photo viewer and orientation editor."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

try:
    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("WebKit", "6.0")
    from gi.repository import Gio, Gtk, WebKit
except (ImportError, ValueError):  # pragma: no cover - platform fallback
    Gio = Gtk = WebKit = None

from km360_viewer import reorient_equirectangular


HTML = r"""<!doctype html><html><head><meta charset="utf-8"><style>
:root{color-scheme:dark;--bg:#11151c;--panel:#1a202b;--panel2:#222a37;--text:#edf2f7;--muted:#9aa7b8;--accent:#57c7ff}
*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;overflow:hidden;background:var(--bg);color:var(--text);font:14px system-ui,sans-serif}
body{display:grid;grid-template-rows:auto 1fr auto}.toolbar,.controls{display:flex;align-items:center;gap:8px;padding:12px 16px;background:var(--bg)}
.title{font-size:20px;font-weight:700;margin-right:8px}button{border:0;border-radius:5px;padding:9px 13px;background:var(--panel2);color:var(--text);font-weight:600;cursor:pointer}
button.primary{background:var(--accent);color:#071018}.check{display:flex;align-items:center;gap:6px;white-space:nowrap}.spacer{flex:1}
#stage{position:relative;min-height:0;margin:0 16px;background:#05070a;overflow:hidden}canvas{display:block;width:100%;height:100%;cursor:crosshair}canvas.dragging{cursor:none}
#guide{pointer-events:none;position:absolute;inset:0}#guide:before{content:"";position:absolute;left:0;right:0;top:50%;border-top:2px dashed var(--accent);opacity:.8}
#reticle{pointer-events:none;position:absolute;left:50%;top:50%;width:20px;height:20px;transform:translate(-50%,-50%);opacity:.9}
#reticle:before,#reticle:after{content:"";position:absolute;background:var(--accent);box-shadow:0 0 2px #000}#reticle:before{left:9px;top:0;width:2px;height:20px}#reticle:after{left:0;top:9px;width:20px;height:2px}
.controls{padding-top:10px;padding-bottom:14px}.controls input[type=range]{width:270px}.muted{color:var(--muted)}
#empty{position:absolute;inset:0;display:grid;place-items:center;color:var(--muted);font-size:18px;pointer-events:none}
</style></head><body>
<div class="toolbar"><span class="title">Sphere Viewer</span><button class="primary" onclick="host('open')">Open media</button><button onclick="resetView()">Reset view</button><button class="primary" onclick="makeLevel()">Make current view level</button><label class="check"><input id="invert" type="checkbox" checked><span aria-hidden="true">👁</span> Invert look</label><span class="spacer"></span><button onclick="toggleFullscreen()">Fullscreen</button><button id="export" onclick="exportCopy()" disabled>Export leveled copy</button></div>
<div id="stage"><canvas id="gl"></canvas><div id="guide"></div><div id="reticle"></div><div id="empty">Open an equirectangular 360° image</div></div>
<div class="controls"><b>Roll</b><input id="roll" type="range" min="-180" max="180" step="0.1" value="0"><span id="rollValue" class="muted">0.0°</span><button onclick="nudgeRoll(-90)">−90°</button><button onclick="nudgeRoll(90)">+90°</button><label class="check"><input id="showGuide" type="checkbox" checked> Horizon guide</label><span class="spacer"></span><span id="status" class="muted">Drag to look • wheel to zoom</span></div>
<script>
const canvas=document.querySelector('#gl'), stage=document.querySelector('#stage'), gl=canvas.getContext('webgl2',{antialias:true,alpha:false});
const vs=`#version 300 es
in vec2 p; out vec2 uv; void main(){uv=p*.5+.5;gl_Position=vec4(p,0.,1.);}`;
const fs=`#version 300 es
precision highp float; in vec2 uv; out vec4 color; uniform sampler2D pano; uniform mat3 orient; uniform float aspect; uniform float tanHalf;
void main(){vec2 q=uv*2.-1.;vec3 ray=normalize(vec3(q.x*aspect*tanHalf,-q.y*tanHalf,1.));vec3 d=orient*ray;float lon=atan(d.x,d.z);float lat=asin(clamp(d.y,-1.,1.));vec2 t=vec2(lon/6.28318530718+.5,.5-lat/3.14159265359);color=texture(pano,t);}`;
function shader(type,src){let s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s}
let prog=null,tex=null,ready=false,pending=false,yaw=0,pitch=0,roll=0,fov=Math.PI/2,committed=[1,0,0,0,1,0,0,0,1];
if(gl){prog=gl.createProgram();gl.attachShader(prog,shader(gl.VERTEX_SHADER,vs));gl.attachShader(prog,shader(gl.FRAGMENT_SHADER,fs));gl.linkProgram(prog);gl.useProgram(prog);let b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),gl.STATIC_DRAW);let loc=gl.getAttribLocation(prog,'p');gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,2,gl.FLOAT,false,0,0);}
function mul(a,b){let o=new Array(9);for(let r=0;r<3;r++)for(let c=0;c<3;c++)o[r*3+c]=a[r*3]*b[c]+a[r*3+1]*b[3+c]+a[r*3+2]*b[6+c];return o}
function rot(y,p,r){let cy=Math.cos(y),sy=Math.sin(y),cp=Math.cos(p),sp=Math.sin(p),cr=Math.cos(r),sr=Math.sin(r);return mul(mul([cy,0,-sy,0,1,0,sy,0,cy],[1,0,0,0,cp,-sp,0,sp,cp]),[cr,-sr,0,sr,cr,0,0,0,1])}
function combined(){return mul(committed,rot(yaw,pitch,roll))}function columnMajor(m){return new Float32Array([m[0],m[3],m[6],m[1],m[4],m[7],m[2],m[5],m[8]])}
function resize(){let d=devicePixelRatio||1,w=Math.max(1,Math.round(stage.clientWidth*d)),h=Math.max(1,Math.round(stage.clientHeight*d));if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h}draw()}
function requestDraw(){if(!pending){pending=true;requestAnimationFrame(()=>{pending=false;draw()})}}
function draw(){if(!gl||!ready)return;gl.viewport(0,0,canvas.width,canvas.height);gl.useProgram(prog);gl.uniformMatrix3fv(gl.getUniformLocation(prog,'orient'),false,columnMajor(combined()));gl.uniform1f(gl.getUniformLocation(prog,'aspect'),canvas.width/canvas.height);gl.uniform1f(gl.getUniformLocation(prog,'tanHalf'),Math.tan(fov/2));gl.drawArrays(gl.TRIANGLES,0,3)}
function loadImage(url,name){let img=new Image();img.onload=()=>{if(tex)gl.deleteTexture(tex);tex=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,tex);gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,false);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.REPEAT);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,img);ready=true;resetView();document.querySelector('#empty').style.display='none';document.querySelector('#export').disabled=false;document.querySelector('#status').textContent=name+' • GPU texture renderer';resize()};img.onerror=()=>host('error','Image could not be decoded');img.src=url}
let drag=null;canvas.addEventListener('pointerdown',e=>{drag=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId);canvas.classList.add('dragging')});canvas.addEventListener('pointermove',e=>{if(!drag)return;let dx=e.clientX-drag[0],dy=e.clientY-drag[1],inv=document.querySelector('#invert').checked?-1:1;yaw+=dx*.004*inv;pitch-=dy*.004*inv;pitch=Math.max(-Math.PI/2+.01,Math.min(Math.PI/2-.01,pitch));drag=[e.clientX,e.clientY];requestDraw()});function endDrag(){drag=null;canvas.classList.remove('dragging')}canvas.addEventListener('pointerup',endDrag);canvas.addEventListener('pointercancel',endDrag);canvas.addEventListener('wheel',e=>{e.preventDefault();fov=Math.max(Math.PI/9,Math.min(2*Math.PI/3,fov*(e.deltaY>0?1.08:.92)));requestDraw()},{passive:false});
const rollInput=document.querySelector('#roll');rollInput.oninput=()=>{roll=Number(rollInput.value)*Math.PI/180;document.querySelector('#rollValue').textContent=Number(rollInput.value).toFixed(1)+'°';requestDraw()};
document.querySelector('#showGuide').onchange=e=>document.querySelector('#guide').style.display=e.target.checked?'block':'none';
function nudgeRoll(d){let v=((Number(rollInput.value)+d+180)%360)-180;rollInput.value=v;rollInput.oninput()}
function resetControls(){yaw=pitch=roll=0;fov=Math.PI/2;rollInput.value=0;document.querySelector('#rollValue').textContent='0.0°'}
function resetView(){committed=[1,0,0,0,1,0,0,0,1];resetControls();requestDraw()}
function makeLevel(){committed=combined();resetControls();document.querySelector('#status').textContent='Current view is level • navigation axes reset';requestDraw()}
function exportCopy(){host('export',JSON.stringify(combined()))}function toggleFullscreen(){document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen()}
function host(action,data=''){window.webkit.messageHandlers.app.postMessage(JSON.stringify({action,data}))}
window.loadPanorama=loadImage;window.addEventListener('resize',resize);new ResizeObserver(resize).observe(stage);resize();
</script></body></html>"""


class SphereWindow:
    def __init__(self, app, path=None):
        self.path = Path(path).resolve() if path else None
        self.window = Gtk.ApplicationWindow(
            application=app, title="KeyMission Sphere Viewer"
        )
        self.window.set_default_size(1280, 820)
        manager = WebKit.UserContentManager()
        manager.register_script_message_handler("app")
        manager.connect("script-message-received::app", self._message)
        self.web = WebKit.WebView(user_content_manager=manager)
        settings = self.web.get_settings()
        settings.set_enable_webrtc(False)
        settings.set_enable_write_console_messages_to_stdout(False)
        self.window.set_child(self.web)
        self.web.connect("load-changed", self._loaded)
        self.web.load_html(HTML, "km360://viewer/")

    def present(self):
        self.window.present()

    def _loaded(self, _web, event):
        if event == WebKit.LoadEvent.FINISHED and self.path:
            self.load(self.path)

    def _eval(self, script):
        self.web.evaluate_javascript(script, -1, None, None, None, None)

    def load(self, path):
        path = Path(path).resolve()
        if path.suffix.lower() in {".mp4", ".mov", ".avi", ".mkv", ".webm"}:
            fallback = Path(__file__).resolve().with_name("km360_viewer.py")
            subprocess.Popen(
                [sys.executable, str(fallback), str(path)], start_new_session=True
            )
            self.window.close()
            return
        if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            self._error("The GPU viewer currently supports JPEG, PNG, and WebP images.")
            return
        try:
            mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
            data = base64.b64encode(path.read_bytes()).decode("ascii")
        except OSError as exc:
            self._error(str(exc))
            return
        self.path = path
        url = f"data:{mime};base64,{data}"
        self._eval(f"loadPanorama({json.dumps(url)},{json.dumps(path.name)})")

    def _message(self, _manager, value):
        try:
            message = json.loads(value.to_string())
        except (TypeError, ValueError, json.JSONDecodeError):
            return
        action = message.get("action")
        if action == "open":
            self._choose_open()
        elif action == "export":
            self._choose_export(message.get("data", ""))
        elif action == "error":
            self._error(message.get("data", "Unknown viewer error"))

    def _choose_open(self):
        dialog = Gtk.FileChooserNative.new(
            "Open 360 image", self.window, Gtk.FileChooserAction.OPEN, "Open", "Cancel"
        )
        image_filter = Gtk.FileFilter()
        image_filter.set_name("360 images")
        for mime in ("image/jpeg", "image/png", "image/webp"):
            image_filter.add_mime_type(mime)
        dialog.add_filter(image_filter)
        dialog.connect(
            "response",
            lambda d, response: self.load(d.get_file().get_path())
            if response == Gtk.ResponseType.ACCEPT
            else None,
        )
        dialog.show()

    def _choose_export(self, matrix_json):
        if not self.path:
            return
        try:
            matrix = np.asarray(json.loads(matrix_json), dtype=float).reshape(3, 3)
        except (ValueError, TypeError, json.JSONDecodeError):
            self._error("The current orientation could not be read.")
            return
        dialog = Gtk.FileChooserNative.new(
            "Export leveled copy",
            self.window,
            Gtk.FileChooserAction.SAVE,
            "Export",
            "Cancel",
        )
        default = self.path.with_name(self.path.stem + "_leveled.jpg")
        dialog.set_current_name(default.name)

        def save(d, response):
            if response != Gtk.ResponseType.ACCEPT:
                return
            target = Path(d.get_file().get_path())
            try:
                source = Image.open(self.path).convert("RGB")
                reorient_equirectangular(source, matrix).save(target, quality=95)
            except Exception as exc:
                self._error(f"Export failed: {exc}")

        dialog.connect("response", save)
        dialog.show()

    def _error(self, text):
        dialog = Gtk.AlertDialog(message="Sphere Viewer", detail=str(text))
        dialog.show(self.window)


def available():
    return Gtk is not None and WebKit is not None


def launch_viewer(path=None):
    """Launch the shared viewer without mixing GTK and Tk event loops."""
    command = [sys.executable, str(Path(__file__).resolve())]
    if path:
        command.append(str(path))
    return subprocess.Popen(command, start_new_session=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?")
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args(argv)
    if args.test:
        assert "getContext('webgl2'" in HTML
        assert "Invert look" in HTML
        print("✓ GPU sphere viewer assets passed")
        return 0
    if not available():
        print("GTK 4 and WebKitGTK 6 are required for the GPU viewer.", file=sys.stderr)
        return 1
    app = Gtk.Application(
        application_id="io.github.innomen.km360.viewer",
        flags=Gio.ApplicationFlags.NON_UNIQUE,
    )
    holder = {}

    def activate(application):
        holder["window"] = SphereWindow(application, args.file)
        holder["window"].present()

    app.connect("activate", activate)
    return app.run([])


if __name__ == "__main__":
    raise SystemExit(main())
