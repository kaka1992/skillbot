"""Tests for clean Agent Panel text streaming."""

from jupyter.magic import _PanelTextStream


def test_plain_text_streams_without_waiting():
    emitted = []
    stream = _PanelTextStream(emitted.append)

    stream.feed("Hello")
    stream.feed(" world")
    stream.finish()

    assert emitted == ["Hello", " world"]


def test_fenced_json_emits_only_unwrapped_text():
    emitted = []
    stream = _PanelTextStream(emitted.append)

    for chunk in ("`", "``json\n", '{"text":"你好\\n\\n**世界**","code":[]}', "\n```"):
        stream.feed(chunk)
    assert emitted == []

    stream.finish()

    assert emitted == ["你好\n\n**世界**"]


def test_invalid_json_falls_back_to_original_text():
    emitted = []
    stream = _PanelTextStream(emitted.append)

    stream.feed('{"text": broken}')
    stream.finish()

    assert emitted == ['{"text": broken}']
