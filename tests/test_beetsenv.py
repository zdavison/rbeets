from beets import config, plugins

from rbeets.beetsenv import open_library


def test_open_library_turns_off_every_file_operation(root, tmp_path):
    open_library(str(root), tmp_path / "state")
    imports = config["import"]
    for key in ("move", "copy", "link", "hardlink", "reflink"):
        assert imports[key].get() is False, key
    assert imports["write"].get() is True
    assert imports["duplicate_action"].get() == "keep"


def test_open_library_ignores_a_beets_config_file(root, tmp_path):
    state = tmp_path / "state"
    state.mkdir()
    (state / "config.yaml").write_text("import:\n  move: yes\nplugins: [fetchart]\n")
    open_library(str(root), state)
    assert config["import"]["move"].get() is False
    assert [p.name for p in plugins.find_plugins()] == ["musicbrainz"]


def test_open_library_puts_the_database_in_the_state_dir(root, tmp_path):
    open_library(str(root), tmp_path / "state")
    assert (tmp_path / "state" / "library.db").exists()


def test_open_library_twice_loads_the_plugins_once(root, tmp_path):
    open_library(str(root), tmp_path / "state")
    open_library(str(root), tmp_path / "state")
    assert len(list(plugins.find_plugins())) == 1


def test_open_library_lets_lookup_errors_reach_rbeets(root, tmp_path):
    # Otherwise beets logs a MusicBrainz error and returns no release, and
    # refresh reports the album as failed with no reason.
    open_library(str(root), tmp_path / "state")
    assert config["raise_on_error"].get(bool) is True
