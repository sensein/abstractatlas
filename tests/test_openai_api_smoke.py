import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import openai_api_smoke


class OpenAISmokeScriptTest(unittest.TestCase):
    def test_get_api_key_reads_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("OPENAI_API_KEY=test-key\n", encoding="utf-8")

            api_key = openai_api_smoke.get_api_key(env_path, "OPENAI_API_KEY")

        self.assertEqual(api_key, "test-key")

    def test_run_responses_returns_elapsed_and_text(self) -> None:
        usage = mock.Mock(input_tokens=3, output_tokens=2, total_tokens=5)
        response = mock.Mock(id="resp_123", output_text="pong", usage=usage)
        client = mock.Mock()
        client.responses.create.return_value = response

        result = openai_api_smoke.run_responses(client, "gpt-test", "ping", 64, None)

        self.assertEqual(result["mode"], "responses")
        self.assertEqual(result["output_text"], "pong")
        self.assertEqual(result["response_id"], "resp_123")

    def test_run_chat_parse_returns_elapsed_and_text(self) -> None:
        parsed = openai_api_smoke.SmokeResponse(answer="pong")
        message = mock.Mock(parsed=parsed)
        choice = mock.Mock(message=message)
        usage = mock.Mock(prompt_tokens=4, completion_tokens=2, total_tokens=6)
        completion = mock.Mock(id="chatcmpl_123", choices=[choice], usage=usage)
        client = mock.Mock()
        client.beta.chat.completions.parse.return_value = completion

        result = openai_api_smoke.run_chat_parse(client, "gpt-test", "ping", 64, None)

        self.assertEqual(result["mode"], "chat-parse")
        self.assertEqual(result["output_text"], "pong")
        self.assertEqual(result["response_id"], "chatcmpl_123")

    def test_main_prints_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("OPENAI_API_KEY=test-key\n", encoding="utf-8")
            with (
                mock.patch("scripts.openai_api_smoke.run_responses", return_value={"mode": "responses", "elapsed_seconds": 0.1, "output_text": "pong", "response_id": "resp_1", "usage": {}}),
                mock.patch("scripts.openai_api_smoke.OpenAI"),
                mock.patch("sys.argv", ["openai_api_smoke.py", "--env-file", str(env_path)]),
                mock.patch("builtins.print") as mocked_print,
            ):
                result = openai_api_smoke.main()

        self.assertEqual(result, 0)
        payload = json.loads(mocked_print.call_args.args[0])
        self.assertEqual(payload["output_text"], "pong")


if __name__ == "__main__":
    unittest.main()
