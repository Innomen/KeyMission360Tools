"""Shared, testable camera operations for KeyMission360 Tools."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import shutil
import subprocess


class CameraError(RuntimeError):
    pass


@dataclass(frozen=True)
class CameraFile:
    number: int
    name: str
    size_bytes: int
    mime: str
    timestamp: int = 0


def _run(*args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CameraError(str(exc)) from exc


def parse_file_list(text: str) -> list[CameraFile]:
    files: list[CameraFile] = []
    for line in text.splitlines():
        if not line.lstrip().startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 7 or not parts[0][1:].isdigit():
            continue
        unit = parts[4].upper()
        scale = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}.get(unit, 1)
        stamp = int(parts[-1]) if parts[-1].isdigit() else 0
        mime = next((p for p in parts[5:-1] if "/" in p), "application/octet-stream")
        files.append(
            CameraFile(int(parts[0][1:]), parts[1], int(parts[3]) * scale, mime, stamp)
        )
    return files


class Camera:
    def connected(self) -> bool:
        p = _run("gphoto2", "--auto-detect")
        return p.returncode == 0 and "KeyMission 360" in p.stdout

    def files(self) -> list[CameraFile]:
        p = _run("gphoto2", "--list-files")
        if p.returncode:
            raise CameraError((p.stderr or "Camera did not answer").strip())
        return parse_file_list(p.stdout)

    def sync_time(self) -> None:
        p = _run("gphoto2", "--set-config", "datetime=now")
        if p.returncode:
            raise CameraError((p.stderr or "Time sync failed").strip())

    def download(self, item: CameraFile, destination: Path) -> tuple[Path, str]:
        destination.mkdir(parents=True, exist_ok=True)
        final = destination / item.name
        partial = final.with_name(final.name + ".partial")
        if final.exists() and abs(final.stat().st_size - item.size_bytes) <= 1024:
            return final, sha256(final)
        p = _run(
            "gphoto2",
            "--get-file",
            str(item.number),
            f"--filename={partial}",
            timeout=1800,
        )
        if p.returncode or not partial.exists():
            raise CameraError((p.stderr or "Download failed").strip())
        if abs(partial.stat().st_size - item.size_bytes) > 1024:
            raise CameraError("Downloaded size does not match the camera object")
        partial.replace(final)
        return final, sha256(final)

    def delete_all(self) -> None:
        before = len(self.files())
        if not before:
            return
        p = _run("gphoto2", "--delete-all-files", "--recurse", timeout=120)
        if p.returncode:
            raise CameraError((p.stderr or "Delete failed").strip())
        remaining = len(self.files())
        if remaining:
            raise CameraError(f"Camera still reports {remaining} object(s)")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dependency_status() -> dict[str, bool]:
    return {
        name: shutil.which(name) is not None
        for name in ("gphoto2", "ffmpeg", "exiftool")
    }
