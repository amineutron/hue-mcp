"""
Tests for the Philips Hue MCP Server

This test suite provides basic tests for the hue_server module.
Run with: pytest
"""

import pytest


def test_rgb_to_xy_pure_red():
    """Test RGB to XY conversion for pure red."""
    from hue_server import rgb_to_xy
    
    result = rgb_to_xy(255, 0, 0)
    assert isinstance(result, list)
    assert len(result) == 2
    # Red should have high x value
    assert result[0] > 0.6
    assert 0 <= result[1] <= 1


def test_rgb_to_xy_pure_green():
    """Test RGB to XY conversion for pure green."""
    from hue_server import rgb_to_xy
    
    result = rgb_to_xy(0, 255, 0)
    assert isinstance(result, list)
    assert len(result) == 2
    # Green should have high y value
    assert result[1] > 0.6
    assert 0 <= result[0] <= 1


def test_rgb_to_xy_pure_blue():
    """Test RGB to XY conversion for pure blue."""
    from hue_server import rgb_to_xy
    
    result = rgb_to_xy(0, 0, 255)
    assert isinstance(result, list)
    assert len(result) == 2
    assert 0 <= result[0] <= 1
    assert 0 <= result[1] <= 1


def test_rgb_to_xy_black():
    """Test RGB to XY conversion for black (should return [0, 0])."""
    from hue_server import rgb_to_xy
    
    result = rgb_to_xy(0, 0, 0)
    assert result == [0.0, 0.0]


def test_rgb_to_xy_white():
    """Test RGB to XY conversion for white."""
    from hue_server import rgb_to_xy
    
    result = rgb_to_xy(255, 255, 255)
    assert isinstance(result, list)
    assert len(result) == 2
    # White should be roughly in the middle
    assert 0.2 <= result[0] <= 0.4
    assert 0.2 <= result[1] <= 0.4


def test_validate_light_id():
    """Test light ID validation."""
    from hue_server import validate_light_id
    
    light_info = {
        "1": {"name": "Light 1"},
        "2": {"name": "Light 2"},
    }
    
    assert validate_light_id(1, light_info) is True
    assert validate_light_id(2, light_info) is True
    assert validate_light_id(3, light_info) is False
    assert validate_light_id(999, light_info) is False


def test_format_light_info():
    """Test light information formatting."""
    from hue_server import format_light_info
    
    light_info = {
        "1": {
            "name": "Living Room",
            "type": "Extended color light",
            "state": {
                "on": True,
                "bri": 254,
                "colormode": "xy",
                "reachable": True,
            },
            "modelid": "LCT015",
            "manufacturername": "Signify",
        }
    }
    
    result = format_light_info(light_info)
    
    assert "1" in result
    assert result["1"]["name"] == "Living Room"
    assert result["1"]["on"] is True
    assert result["1"]["brightness"] == 254
    assert result["1"]["reachable"] is True


# Integration tests would require a mock Hue bridge
# or actual hardware, which we'll skip for now

@pytest.mark.skip(reason="Requires Hue bridge hardware")
def test_bridge_connection():
    """Test connection to Hue bridge."""
    pass


@pytest.mark.skip(reason="Requires Hue bridge hardware")
def test_get_all_lights():
    """Test getting all lights from bridge."""
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


LIGHTS = {
    "1": {"name": "Salon", "type": "Extended color light", "state": {"on": False}},
    "2": {"name": "Lampe salon", "type": "Extended color light", "state": {"on": False}},
    "3": {"name": "Bureau", "type": "Dimmable light", "state": {"on": True}},
}


@pytest.mark.parametrize("query, expected", [
    ("Salon", "1"),          # exact match wins over the partial "Lampe salon"
    ("salón", "1"),          # case and accent insensitive
    ("bur", "3"),            # unique partial match
    ("LAMPE", "2"),
])
def test_resolve_name_matches(query, expected):
    from hue_server import resolve_name

    names = {i: light["name"] for i, light in LIGHTS.items()}
    assert resolve_name(query, names, "light") == (expected, None)


def test_resolve_name_reports_ambiguous_and_missing_names():
    from hue_server import resolve_name

    names = {"1": "Lampe salon", "2": "Lampe bureau"}
    lid, error = resolve_name("lampe", names, "light")
    assert lid is None and "ambiguous" in error and "Lampe salon" in error and "Lampe bureau" in error
    lid, error = resolve_name("cuisine", names, "light")
    assert lid is None and "no light named" in error


def test_resolve_light_id_prefers_the_id():
    from hue_server import resolve_light_id

    assert resolve_light_id(3, "Salon", LIGHTS) == (3, None)
    assert resolve_light_id(0, "Salon", LIGHTS) == (1, None)
    assert resolve_light_id(9, "", LIGHTS)[1] == "Error: Light with ID 9 not found."
    assert resolve_light_id(0, "", LIGHTS)[0] is None


def _ctx_with_bridge(monkeypatch, bridge, light_info=LIGHTS):
    from unittest.mock import MagicMock

    import hue_server

    monkeypatch.setattr(hue_server, "get_bridge_ctx", lambda ctx: (bridge, light_info))
    return MagicMock()


def test_turn_on_light_by_name(monkeypatch):
    from unittest.mock import MagicMock

    from hue_server import turn_on_light

    bridge = MagicMock()
    ctx = _ctx_with_bridge(monkeypatch, bridge)
    assert turn_on_light(ctx, light_name="bureau") == "Light 3 (Bureau) turned on."
    bridge.set_light.assert_called_once_with(3, "on", True)


def test_activate_scene_by_name_uses_the_scene_room(monkeypatch):
    from unittest.mock import MagicMock

    from hue_server import activate_scene_by_name

    bridge = MagicMock()
    bridge.get_scene.return_value = {
        "abc": {"name": "Soirée", "group": "5"},
        "def": {"name": "Lecture"},  # LightScene: no group
    }
    bridge.get_group.side_effect = lambda gid=None: {5: {"name": "Living room"}}.get(gid, {}) if gid else {"5": {}}
    ctx = _ctx_with_bridge(monkeypatch, bridge)

    assert activate_scene_by_name("soiree", ctx) == "Scene 'Soirée' applied to group 'Living room'."
    bridge.set_group.assert_called_with(5, "scene", "abc")
    assert activate_scene_by_name("lecture", ctx) == "Scene 'Lecture' applied to group 'all lights'."
    bridge.set_group.assert_called_with(0, "scene", "def")
