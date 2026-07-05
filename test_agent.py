import unittest
from unittest.mock import MagicMock, patch
import json

from mcp_client import WorkspaceMCPClient
from agent import TriageAgent

class TestWorkspaceMCPClient(unittest.TestCase):
    def setUp(self):
        self.mock_creds = MagicMock()
        self.mock_creds.valid = True
        self.mock_creds.token = "fake-token"
        self.client = WorkspaceMCPClient(self.mock_creds)

    def test_parse_mcp_result_json(self):
        # Mock MCP output with JSON-encoded text content
        raw_mcp_res = {
            "content": [
                {
                    "type": "text",
                    "text": '{"threads": [{"id": "thread123", "snippet": "Hello"}]}'
                }
            ]
        }
        parsed = self.client._parse_mcp_result(raw_mcp_res)
        self.assertIn("threads", parsed)
        self.assertEqual(parsed["threads"][0]["id"], "thread123")

    def test_parse_mcp_result_raw_text(self):
        # Mock MCP output with non-JSON plain text
        raw_mcp_res = {
            "content": [
                {
                    "type": "text",
                    "text": "Success"
                }
            ]
        }
        parsed = self.client._parse_mcp_result(raw_mcp_res)
        self.assertEqual(parsed, "Success")

    def test_parse_mcp_result_empty(self):
        parsed = self.client._parse_mcp_result({})
        self.assertEqual(parsed, {})


class TestTriageAgentWiring(unittest.TestCase):
    def test_agent_initialization(self):
        mock_mcp = MagicMock()
        agent = TriageAgent(mock_mcp)
        self.assertEqual(agent.mcp_client, mock_mcp)

if __name__ == "__main__":
    unittest.main()
