import pytest

from app.services.ai_service import AIService


class TestParseResponse:
    def setup_method(self) -> None:
        self.service = AIService.__new__(AIService)

    def test_parse_valid_json(self) -> None:
        assert self.service._parse_response('{"key": "val"}') == {"key": "val"}

    def test_parse_json_code_block(self) -> None:
        text = 'text\n```json\n{"key": "val"}\n```\nmore'
        assert self.service._parse_response(text) == {"key": "val"}

    def test_parse_json_in_text(self) -> None:
        assert self.service._parse_response('blah {"k": 1} blah') == {"k": 1}

    def test_parse_invalid_raises(self) -> None:
        with pytest.raises(Exception):
            self.service._parse_response("no json here at all")

    def test_parse_nested_json(self) -> None:
        text = '{"foods": [{"name": "soup", "cal": 50}]}'
        result = self.service._parse_response(text)
        assert len(result["foods"]) == 1
