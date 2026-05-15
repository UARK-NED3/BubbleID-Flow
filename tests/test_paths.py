from pathlib import Path

from bubbleid_flow.paths import iter_images
from bubbleid_flow.preprocess import parse_roi


def test_iter_images_finds_supported_extensions(tmp_path: Path) -> None:
    (tmp_path / "a.bmp").write_bytes(b"")
    (tmp_path / "b.txt").write_text("")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "c.JPG").write_bytes(b"")

    assert [path.name for path in iter_images(tmp_path)] == ["a.bmp", "c.JPG"]


def test_parse_roi() -> None:
    assert parse_roi("1, 2, 30, 40") == (1, 2, 30, 40)
