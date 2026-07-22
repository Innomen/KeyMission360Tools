# Sphere Viewer architecture

## Product boundary

The sphere viewer is one component with two launch surfaces:

1. KeyMission 360 Tools opens camera or downloaded media in the viewer.
2. KeyMission Sphere Viewer opens local media directly from the application menu,
   file manager, drag and drop, or command line.

Both surfaces must use the same pose model, renderer, shortcuts, media controls,
and export path. The camera manager must not become a second viewer implementation.

## SphereView audit

The installed `io.github.dynobo.sphereview` 0.1.6 is a GTK/libadwaita desktop
shell around WebKitGTK. Its embedded page uses Photo Sphere Viewer 5.14.1, which
uses Three.js/WebGL for the actual texture rendering and interaction. The shell:

- reads a whole image into memory and transfers it to JavaScript as base64;
- supports JPEG, PNG, and WebP images;
- provides open, drag-and-drop, fullscreen, navbar, keyboard controls, and autorotate;
- deliberately disables WebKit media support;
- does not interpret or edit panorama orientation;
- does not offer horizon leveling, corrected export, video, library navigation,
  metadata inspection, or pose persistence.

The transferable lesson is the GPU texture renderer and mature input dynamics, not
the thin application shell or its file-transfer method.

## Core model

Keep three states distinct:

- **source orientation**: metadata supplied by the camera or file;
- **committed panorama orientation**: the user's non-destructive correction;
- **view pose**: transient yaw, pitch, roll, and field of view used while looking.

`Make current view level` composes the current view pose into the committed
orientation, then resets the view pose. The visible image must not jump, and new
navigation input must remain screen-relative. Export applies source and committed
orientation to the equirectangular pixels without overwriting the original.

## Rendering boundary

Interactive rendering and export have different jobs:

- **interactive path**: GPU texture sampling at display refresh rate, inertial drag,
  smooth wheel/pinch zoom, and frame-timed video textures;
- **export path**: CPU or compute remapping at source resolution with high-quality
  interpolation, metadata preservation, cancellation, and progress reporting.

The current NumPy/OpenCV projector remains a portable fallback and export oracle.
It should not remain the primary interactive renderer.

## Delivery sequence

1. Establish the shared standalone/embedded launch contract and desktop handlers.
2. Add the GPU renderer behind the existing viewer API, retaining CPU fallback.
3. Add image sequencing, drag-and-drop, fullscreen, shortcuts, fit/zoom, autorotate,
   and persistent per-file pose sidecars.
4. Add native-rate spherical video playback, scrub/audio controls, and corrected
   video export through FFmpeg.
5. Add metadata diagnostics, projection validation, thumbnail/library browsing,
   comparison/reset, and optional automatic horizon suggestions.

Original media is always read-only. Corrections are stored separately until the
user explicitly exports a new file.
