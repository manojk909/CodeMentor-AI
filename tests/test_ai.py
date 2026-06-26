import unittest
from unittest.mock import patch, MagicMock
import os
import json

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SESSION_SECRET'] = 'test-secret'

from app import app, db
from app.models import User, PlatformStats, Problem, ProblemSolved
from app.ai import get_ai_provider
from app.ai.openai_provider import OpenAIProvider
from app.ai.claude_provider import ClaudeProvider
from app.ai.gemini_provider import GeminiProvider
from app.ai.local_provider import LocalSampleProvider
from app.ai.tutor import AITutor

class TestAI(unittest.TestCase):
    def setUp(self):
        self.ctx = app.app_context()
        self.ctx.push()
        db.create_all()
        
        # Create test user
        self.user = User(username="test_ai_user", email="ai@example.com")
        self.user.set_password("password")
        self.user.learning_goals = "Learn dynamic programming"
        self.user.target_companies = "Google"
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    @patch.dict(os.environ, {}, clear=True)
    def test_get_ai_provider_fallback(self):
        # With empty env, should fall back to LocalSampleProvider
        provider = get_ai_provider()
        self.assertIsInstance(provider, LocalSampleProvider)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-openai-key"})
    def test_get_ai_provider_openai(self):
        provider = get_ai_provider()
        self.assertIsInstance(provider, OpenAIProvider)
        self.assertEqual(provider.api_key, "test-openai-key")

    @patch.dict(os.environ, {"CLAUDE_API_KEY": "test-claude-key"})
    def test_get_ai_provider_claude(self):
        # Note: priority is OpenAI first, so we patch dict without OpenAI
        provider = get_ai_provider()
        self.assertIsInstance(provider, ClaudeProvider)
        self.assertEqual(provider.api_key, "test-claude-key")

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-gemini-key"})
    def test_get_ai_provider_gemini(self):
        provider = get_ai_provider()
        self.assertIsInstance(provider, GeminiProvider)
        self.assertEqual(provider.api_key, "test-gemini-key")

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-openrouter-key"})
    def test_get_ai_provider_openrouter(self):
        provider = get_ai_provider()
        self.assertIsInstance(provider, OpenAIProvider)
        self.assertEqual(provider.api_key, "test-openrouter-key")
        self.assertEqual(provider.base_url, "https://openrouter.ai/api/v1")

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-deepseek-key"})
    def test_get_ai_provider_deepseek(self):
        provider = get_ai_provider()
        self.assertIsInstance(provider, OpenAIProvider)
        self.assertEqual(provider.api_key, "test-deepseek-key")
        self.assertEqual(provider.base_url, "https://api.deepseek.com/v1")

    @patch('requests.post')
    def test_openai_provider_completion(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'OpenAI Response Text'
                }
            }]
        }
        mock_post.return_value = mock_response
        
        provider = OpenAIProvider(api_key="key")
        result = provider.generate_completion("Hello", response_format="text")
        self.assertEqual(result, "OpenAI Response Text")
        mock_post.assert_called_once()

    @patch('requests.post')
    def test_claude_provider_completion(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'content': [{
                'text': 'Claude Response Text'
            }]
        }
        mock_post.return_value = mock_response
        
        provider = ClaudeProvider(api_key="key")
        result = provider.generate_completion("Hello", response_format="text")
        self.assertEqual(result, "Claude Response Text")
        mock_post.assert_called_once()

    @patch('google.genai.Client')
    def test_gemini_provider_completion(self, mock_client_class):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Gemini Response Text"
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        provider = GeminiProvider(api_key="key")
        result = provider.generate_completion("Hello", response_format="text")
        self.assertEqual(result, "Gemini Response Text")
        mock_client.models.generate_content.assert_called_once()

    def test_tutor_build_context(self):
        # Create some stats
        stats = PlatformStats(
            user_id=self.user.id,
            platform="leetcode",
            total_problems=15,
            easy_solved=10,
            medium_solved=5,
            hard_solved=0
        )
        # Create a problem and solved entry
        prob = Problem(title="Two Sum", platform="leetcode", difficulty="Easy", category="Arrays")
        db.session.add(stats)
        db.session.add(prob)
        db.session.commit()
        
        solved = ProblemSolved(user_id=self.user.id, problem_id=prob.id)
        db.session.add(solved)
        db.session.commit()
        
        tutor = AITutor()
        ctx_str = tutor._build_user_context(self.user, [stats], [solved])
        
        self.assertIn("User: test_ai_user", ctx_str)
        self.assertIn("Learning Goals: Learn dynamic programming", ctx_str)
        self.assertIn("Target Companies: Google", ctx_str)
        self.assertIn("leetcode: 15 problems solved", ctx_str)
        self.assertIn("Two Sum (Easy - Arrays)", ctx_str)

    @patch.object(LocalSampleProvider, 'generate_completion')
    def test_tutor_recommendations(self, mock_completion):
        mock_completion.return_value = '{"week_1": {"focus": "Arrays"}}'
        
        tutor = AITutor()
        # Force the tutor's provider to be our mocked provider
        tutor.provider = LocalSampleProvider()
        
        res = tutor.get_recommendation(self.user.id, 'study_plan', "Custom query")
        self.assertEqual(res, '{"week_1": {"focus": "Arrays"}}')
        mock_completion.assert_called_once()

    def test_tutor_chat_fallback(self):
        tutor = AITutor()
        response = tutor.chat_with_tutor(self.user.id, "Explain linked list")
        self.assertIn("linked list", response.lower())
        self.assertIn("nodes", response.lower())
