from wastickers import _to_snake_case


def test_to_snake_case():
    tsc = _to_snake_case
    assert tsc("Normal sentence.") == "normal_sentence"
    assert tsc("Newline\nsentence!") == "newline_sentence"
    assert tsc("PascalCase") == "pascalcase"
    assert tsc("camelCase") == "camelcase"
    assert tsc("snake_case") == "snake_case"
    assert tsc("Dash-case") == "dash_case"
    assert tsc("multi  __ whitespace") == "multi_whitespace"
    assert tsc("Non-standard! 😀@ characters &%^()") == "non_standard_characters"
