import json
import os
import unittest
from io import BytesIO
from unittest.mock import MagicMock
from unittest.mock import patch

import app as web_app
from chatbot import SYSTEM_PROMPT, format_report, generate_hosted_response


class ChatApiTests(unittest.TestCase):
    def setUp(self):
        web_app.app.config.update(TESTING=True)
        self.client = web_app.app.test_client()

    def test_homepage_renders_chat_interface(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"KARAN'S PERSONAL AI", response.data)
        self.assertIn(b"Write a report", response.data)

    def test_static_assets_are_served(self):
        response = self.client.get("/static/app.js")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"checkModelStatus", response.data)
        response.close()

    def test_assistant_is_personalized_for_karan_and_reports(self):
        self.assertIn("Karan Ambhore", SYSTEM_PROMPT)
        self.assertIn("reports", SYSTEM_PROMPT)
        self.assertIn("Never invent facts", SYSTEM_PROMPT)
        self.assertIn("only source", SYSTEM_PROMPT)
        self.assertIn("do not claim access to his files", SYSTEM_PROMPT)

    def test_report_mode_formats_only_provided_notes(self):
        answer = format_report(
            "/report\nTitle: Project update\n- Redesign finished\n- Next: mobile testing"
        )

        self.assertIn("Project update", answer)
        self.assertIn("- Redesign finished", answer)
        self.assertIn("- Next: mobile testing", answer)
        self.assertNotIn("client", answer.lower())

    def test_report_mode_requests_notes_when_empty(self):
        answer = format_report("/report")

        self.assertIn("Add your source notes", answer)

    @patch("app.model_files_available", return_value=False)
    def test_status_reports_missing_model(self, model_available):
        response = self.client.get("/api/status")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json["model_available"])
        model_available.assert_called_once_with()

    @patch.dict(
        os.environ,
        {
            "VERCEL": "1",
            "AI_API_KEY": "test-key",
            "AI_BASE_URL": "https://provider.example/v1",
            "AI_MODEL": "test-model",
        },
        clear=True,
    )
    @patch("app.model_files_available", return_value=False)
    def test_status_reports_hosted_ai_ready(self, _model_available):
        response = self.client.get("/api/status")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["hosted_ai_available"])
        self.assertTrue(response.json["ai_available"])
        self.assertEqual(response.json["hosting_mode"], "vercel")
        self.assertNotIn("test-key", response.get_data(as_text=True))

    @patch("app.model_files_available", return_value=False)
    def test_chat_explains_how_to_install_missing_model(self, model_available):
        response = self.client.post("/api/chat", json={"message": "Hello"})

        self.assertEqual(response.status_code, 503)
        self.assertIn("download_model.py", response.json["error"])
        model_available.assert_called_once_with()

    def test_chat_rejects_empty_message(self):
        response = self.client.post("/api/chat", json={"message": "  "})

        self.assertEqual(response.status_code, 400)
        self.assertIn("Enter a message", response.json["error"])

    @patch.dict(os.environ, {"VERCEL": "1"}, clear=True)
    @patch("app.model_files_available", return_value=False)
    def test_vercel_chat_requires_hosted_provider_configuration(self, _model_available):
        response = self.client.post("/api/chat", json={"message": "Hello"})

        self.assertEqual(response.status_code, 503)
        self.assertIn("AI_API_KEY", response.json["error"])

    @patch.dict(
        os.environ,
        {
            "AI_API_KEY": "test-key",
            "AI_BASE_URL": "https://provider.example/v1",
            "AI_MODEL": "test-model",
        },
        clear=True,
    )
    @patch("app.generate_hosted_response", return_value="Hosted answer.")
    @patch("app.model_files_available", return_value=False)
    def test_chat_uses_hosted_provider_without_local_model(
        self,
        _model_available,
        generate_hosted,
    ):
        history = [{"role": "user", "content": "Earlier question"}]
        response = self.client.post(
            "/api/chat",
            json={"message": "Follow-up", "history": history},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"answer": "Hosted answer."})
        generate_hosted.assert_called_once_with("Follow-up", history)

    @patch.dict(
        os.environ,
        {
            "AI_API_KEY": "test-key",
            "AI_BASE_URL": "https://provider.example/v1/",
            "AI_MODEL": "test-model",
        },
        clear=True,
    )
    @patch("chatbot.urlopen")
    def test_hosted_provider_request_uses_configured_model_and_messages(self, urlopen):
        provider_response = MagicMock()
        provider_response.__enter__.return_value.read.return_value = json.dumps(
            {"choices": [{"message": {"content": "Hosted response."}}]}
        ).encode()
        urlopen.return_value = provider_response

        answer = generate_hosted_response(
            "Hello",
            [{"role": "user", "content": "Earlier"}],
        )

        self.assertEqual(answer, "Hosted response.")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://provider.example/v1/chat/completions")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        body = json.loads(request.data)
        self.assertEqual(body["model"], "test-model")
        self.assertEqual(
            [message["role"] for message in body["messages"]],
            ["system", "user", "user"],
        )

    @patch.dict(
        os.environ,
        {
            "AI_API_KEY": "test-key",
            "AI_BASE_URL": "http://provider.example/v1",
            "AI_MODEL": "test-model",
        },
        clear=True,
    )
    def test_hosted_provider_rejects_insecure_base_url(self):
        with self.assertRaisesRegex(ValueError, "must use HTTPS"):
            generate_hosted_response("Hello")

    @patch.dict(
        os.environ,
        {
            "AI_API_KEY": "test-key",
            "AI_BASE_URL": "http://provider.example/v1",
            "AI_MODEL": "test-model",
        },
        clear=True,
    )
    def test_insecure_hosted_provider_is_not_reported_ready(self):
        with patch("app.model_files_available", return_value=False):
            response = self.client.get("/api/status")

        self.assertFalse(response.json["hosted_ai_available"])
        self.assertFalse(response.json["ai_available"])

    @patch("app.model_files_available", return_value=True)
    @patch("app.generate_response", return_value="A helpful answer.")
    def test_chat_passes_recent_history_to_local_model(self, generate, model_available):
        history = [{"role": "user", "content": "Earlier question"}]
        response = self.client.post(
            "/api/chat",
            json={"message": "Follow-up", "history": history},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"answer": "A helpful answer."})
        generate.assert_called_once_with("Follow-up", history)
        model_available.assert_called_once_with()

    @patch("app.model_files_available", return_value=True)
    @patch("app.generate_response")
    def test_report_mode_does_not_call_language_model(self, generate, _model_available):
        response = self.client.post(
            "/api/chat",
            json={"message": "/report\nWebsite redesign finished.\nSeven tests passed."},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Website redesign finished.", response.json["answer"])
        self.assertIn("Seven tests passed.", response.json["answer"])
        generate.assert_not_called()

    def test_chat_rejects_invalid_history(self):
        response = self.client.post(
            "/api/chat",
            json={"message": "Hello", "history": [{"role": "system", "content": "No"}]},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("history is invalid", response.json["error"])


if __name__ == "__main__":
    unittest.main()
