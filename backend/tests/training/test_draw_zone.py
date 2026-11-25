"""draw_zone.py: keys driven headlessly (no real OpenCV window)."""

import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "training"))

import draw_zone as dz  # noqa: E402

B, N, Q, ESC, ENTER, U, Y, R = ord("b"), ord("n"), ord("q"), 27, 13, ord("u"), ord("y"), ord("r")
CLICK = "click"


@pytest.fixture
def photo(tmp_path):
    path = tmp_path / "clip.png"
    dz.cv2.imwrite(str(path), np.zeros((100, 200, 3), np.uint8))
    return path


def run(monkeypatch, path, events):
    """Feed keys and clicks to draw(); a click is (CLICK, x, y)."""
    callback = {}
    queue = list(events)

    def wait_key(_ms):
        while queue and isinstance(queue[0], tuple):
            _, x, y = queue.pop(0)
            callback["fn"](dz.cv2.EVENT_LBUTTONDOWN, x, y, 0, None)
        return queue.pop(0) if queue else Q

    monkeypatch.setattr(dz.cv2, "namedWindow", lambda *a: None)
    monkeypatch.setattr(dz.cv2, "setMouseCallback", lambda _t, fn: callback.update(fn=fn))
    monkeypatch.setattr(dz.cv2, "imshow", lambda *a: None)
    monkeypatch.setattr(dz.cv2, "destroyWindow", lambda *a: None)
    monkeypatch.setattr(dz.cv2, "waitKey", wait_key)
    return dz.draw(path, 0)


def test_leave_or_warn():
    assert dz.leave_or_warn(B, changed=False, armed=None) == ("back", None)
    assert dz.leave_or_warn(B, changed=True, armed=None) == (None, B)
    assert dz.leave_or_warn(B, changed=True, armed=B) == ("back", None)
    assert dz.leave_or_warn(N, changed=True, armed=B) == (None, N)   # a different key starts over


@pytest.mark.parametrize("key,result", [(B, "back"), (N, "skipped"), (Q, "quit"), (ESC, "quit")])
def test_leave_keys_act_at_once_without_changes(monkeypatch, photo, key, result):
    assert run(monkeypatch, photo, [key]) == result


def test_unsaved_points_need_the_key_twice(monkeypatch, photo, capsys):
    events = [(CLICK, 10, 10), (CLICK, 50, 10), (CLICK, 50, 50), B, B]
    assert run(monkeypatch, photo, events) == "back"
    assert "unsaved changes" in capsys.readouterr().out
    assert not dz.sidecar(photo).exists()


def test_a_click_between_the_two_presses_rearms_the_warning(monkeypatch, photo):
    # the second N only warns again (clicks came between), so Enter still saves
    events = [(CLICK, 10, 10), N, (CLICK, 50, 10), (CLICK, 50, 50), N, ENTER]
    assert run(monkeypatch, photo, events) == "saved"


def test_saved_zone_loads_and_counts_as_unchanged(monkeypatch, photo):
    events = [(CLICK, 10, 10), (CLICK, 50, 10), (CLICK, 50, 50), ENTER]
    assert run(monkeypatch, photo, events) == "saved"
    assert len(json.loads(dz.sidecar(photo).read_text())["points"]) == 3
    assert run(monkeypatch, photo, [B]) == "back"            # reopened, untouched: leaves at once
    assert run(monkeypatch, photo, [U, B, B]) == "back"      # an undo is a change: warns first


def test_undo_redo_and_reset(monkeypatch, photo):
    events = [(CLICK, 10, 10), (CLICK, 50, 10), (CLICK, 50, 50), R, Y, Y, Y, U, Y, ENTER]
    assert run(monkeypatch, photo, events) == "saved"
    assert len(json.loads(dz.sidecar(photo).read_text())["points"]) == 3
