"""Storage keys map to files under STORAGE_DIR and can never escape it."""

import pytest

from app.core import config
from app.services import storage_service


def test_keys_resolve_inside_the_storage_folder():
    path = storage_service.path_for("media/abc/original.jpg")
    assert path == config.STORAGE_DIR / "media" / "abc" / "original.jpg"
    assert storage_service.media_key("abc", "crops", "01.jpg") == "media/abc/crops/01.jpg"


@pytest.mark.parametrize("bad", ["../secret.txt", "media/../../x", "/etc/passwd", "C:/Windows/x", ""])
def test_keys_that_escape_the_folder_are_rejected(bad):
    with pytest.raises(storage_service.InvalidKey):
        storage_service.path_for(bad)


def test_put_file_put_bytes_exists_and_delete(tmp_path):
    source = tmp_path / "photo.jpg"
    source.write_bytes(b"jpeg bytes")
    key = storage_service.put_file(storage_service.media_key("m1", "original.jpg"), source)
    storage_service.put_bytes(storage_service.media_key("m1", "crops", "01.jpg"), b"crop")

    assert storage_service.exists(key)
    assert storage_service.path_for(key).read_bytes() == b"jpeg bytes"
    assert not storage_service.exists(None)

    storage_service.delete_prefix("media/m1")
    assert not storage_service.exists(key)
    storage_service.delete_prefix("media/m1")   # deleting twice is fine


def test_sha256_identifies_identical_content(tmp_path):
    a, b, c = tmp_path / "a", tmp_path / "b", tmp_path / "c"
    a.write_bytes(b"same")
    b.write_bytes(b"same")
    c.write_bytes(b"different")
    assert storage_service.sha256_of(a) == storage_service.sha256_of(b) != storage_service.sha256_of(c)
    assert len(storage_service.sha256_of(a)) == 64
