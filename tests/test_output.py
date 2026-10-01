from rbeets.output import human_handler


def test_human_output_shows_the_proposed_match(capsys):
    human_handler(
        {
            "type": "progress",
            "done": 3,
            "total": 620,
            "album": "Artist - Album",
            "outcome": "proposed",
            "match": "Artist - Album (Remaster)",
            "release": "11111111-1111-4111-8111-111111111111",
            "distance": 0.012,
        }
    )
    line = capsys.readouterr().err
    assert "Artist - Album (Remaster)" in line
    assert "0.012" in line
    assert "11111111-1111-4111-8111-111111111111" in line


def test_human_output_without_a_match_shows_the_outcome_only(capsys):
    human_handler({"type": "progress", "done": 1, "total": 2, "album": "A - B", "outcome": "skipped", "match": None})
    assert capsys.readouterr().err == "1/2 A - B (skipped)\n"
