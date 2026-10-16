from pathlib import Path

import pytest

from vzrecon.config import Config, PRESETS

def _write(tmp_path, body):
    p = Path(tmp_path) / "c.toml"
    p.write_text(body)
    return p

def test_defaults():
    Config().validate()

def test_toml(tmp_path):
    p = _write(tmp_path, 'workers = 500\ntarget_port = 8080\n')
    c = Config.from_toml(p)
    assert c.workers == 500
    assert c.target_port == 8080

def test_unknown(tmp_path):
    p = _write(tmp_path, 'nope = 1\n')
    with pytest.raises(ValueError):
        Config.from_toml(p)

def test_bad_port():
    with pytest.raises(ValueError):
        Config(target_port=0).validate()

def test_bad_format():
    with pytest.raises(ValueError):
        Config(format="xml").validate()

def test_preset():
    c = Config().apply_preset("stealth")
    assert c.workers == PRESETS["stealth"]["workers"]

def test_bad_preset():
    with pytest.raises(ValueError):
        Config().apply_preset("nope")
