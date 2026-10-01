from rbeets import cli


def test_a_bad_target_is_a_usage_error():
    assert _exit_code(["host-without-root", "version"]) == 1


def test_an_unknown_command_is_a_usage_error():
    assert _exit_code(["host:/music", "rm"]) == 1


def test_restrict_needs_one_key_file():
    assert _exit_code(["host:/music", "restrict"]) == 1


def test_restrict_with_a_missing_key_file_is_a_usage_error(tmp_path):
    assert _exit_code(["host:/music", "restrict", str(tmp_path / "missing.pub")]) == 1


def _exit_code(argv: list[str]) -> int:
    try:
        return cli.run(argv)
    except SystemExit as exc:
        return exc.code
