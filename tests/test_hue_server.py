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


def test_phue_logger_does_not_log_the_bridge_username():
    """phue logs 'Using username: <secret>' at INFO; it must stay silent at that level."""
    import logging

    import hue_server  # noqa: F401  (importing configures the loggers)

    assert logging.getLogger("phue").getEffectiveLevel() >= logging.WARNING


async def test_saved_config_is_owner_only(tmp_path, monkeypatch):
    """The config file stores the bridge username (pairing secret): mode 0600, dir 0700."""
    import stat
    from unittest.mock import MagicMock

    import hue_server

    config_dir = tmp_path / "hue-mcp"
    monkeypatch.setattr(hue_server, "CONFIG_DIR", str(config_dir))
    monkeypatch.setattr(hue_server, "CONFIG_FILE", str(config_dir / "config.json"))
    monkeypatch.setattr(hue_server, "BRIDGE_IP", "192.0.2.10")
    bridge = MagicMock(ip="192.0.2.10", username="secret-username")
    bridge.get_light.return_value = {}
    monkeypatch.setattr(hue_server, "Bridge", MagicMock(return_value=bridge))

    async with hue_server.hue_lifespan(MagicMock()):
        pass

    assert stat.S_IMODE((config_dir / "config.json").stat().st_mode) == 0o600
    assert stat.S_IMODE(config_dir.stat().st_mode) == 0o700
