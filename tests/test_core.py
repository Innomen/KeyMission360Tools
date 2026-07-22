from pathlib import Path
import tempfile
import unittest

from km360_core import parse_file_list, sha256
from km360_gui import human_size
from km360_viewer import Projector, reorient_equirectangular
from PIL import Image


SAMPLE = """There are 2 files in folder '/store'.
#1     TEST0001.MP4               rd 18176 KB video/mpeg 1776478610
#2     TEST0002.JPG               rd 11945 KB 7744x3872 image/jpeg 1776478614
"""


class CoreTests(unittest.TestCase):
    def test_parses_gphoto_rows(self):
        files = parse_file_list(SAMPLE)
        self.assertEqual(2, len(files))
        self.assertEqual("TEST0001.MP4", files[0].name)
        self.assertEqual(18176 * 1024, files[0].size_bytes)
        self.assertEqual("image/jpeg", files[1].mime)

    def test_ignores_noise(self):
        self.assertEqual([], parse_file_list("camera unavailable\n"))

    def test_hashes_in_chunks(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.bin"
            path.write_bytes(b"abc")
            self.assertEqual(
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
                sha256(path),
            )

    def test_human_size(self):
        self.assertEqual("1.0 MB", human_size(1024 * 1024))

    def test_spherical_orientation_preserves_canvas(self):
        source = Image.new("RGB", (512, 256), "navy")
        output = reorient_equirectangular(source, 0, 0, 1.5708)
        self.assertEqual(source.size, output.size)

    def test_rectilinear_projection_size(self):
        source = Image.new("RGB", (512, 256), "navy")
        self.assertEqual((320, 200), Projector(320, 200).project(source).size)


if __name__ == "__main__":
    unittest.main()
