import json

import pytest

from app.core.errors import ValidationFailed
from app.utils.zone_validation import parse_zone_points, validate_zone_in_frame


def test_valid_zone_is_parsed_to_floats():
    pts = parse_zone_points("[[0,0],[100,0],[100,50]]")
    assert pts == [[0.0, 0.0], [100.0, 0.0], [100.0, 50.0]]


def test_triangle_with_float_coordinates_is_fine():
    assert len(parse_zone_points(json.dumps([[0.5, 0.5], [10.25, 0], [5, 9.75]]))) == 3


@pytest.mark.parametrize("raw", ["", "null", "123", '"abc"', "[[1,2],[3,4]]", "[[1,2,3],[4,5,6],[7,8,9]]"])
def test_malformed_zones_are_rejected(raw):
    with pytest.raises(ValidationFailed):
        parse_zone_points(raw)


def test_collinear_points_have_no_area():
    with pytest.raises(ValidationFailed, match="no area"):
        parse_zone_points("[[0,0],[5,5],[10,10]]")


def test_infinite_values_are_rejected():
    with pytest.raises(ValidationFailed, match="Point 2"):
        parse_zone_points("[[0,0],[Infinity,5],[10,10]]")


def test_points_on_the_frame_edge_are_inside():
    zone = [[0, 0], [320, 0], [320, 240], [0, 240]]
    assert validate_zone_in_frame([[float(x), float(y)] for x, y in zone], 320, 240) == zone


@pytest.mark.parametrize("bad", [[-1.0, 5.0], [5.0, -1.0], [321.0, 5.0], [5.0, 241.0]])
def test_point_outside_the_frame_is_rejected_with_the_frame_size(bad):
    with pytest.raises(ValidationFailed, match="320x240"):
        validate_zone_in_frame([[0.0, 0.0], [10.0, 0.0], bad], 320, 240)


def test_in_frame_points_are_rounded_to_whole_pixels():
    assert validate_zone_in_frame([[0.4, 0.6], [10.5, 0.0], [5.0, 9.9]], 320, 240) == [[0, 1], [10, 0], [5, 10]]
