import unittest
from app.services.code_executor import CodeExecutor

class TestCodeExecutor(unittest.TestCase):
    def setUp(self):
        self.executor = CodeExecutor()

    def test_run_python_success(self):
        code = "print(10 + 20)"
        result = self.executor.execute_code(code, 'python')
        self.assertTrue(result['success'])
        self.assertEqual(result['output'], '30')
        self.assertEqual(result['status'], 'success')

    def test_run_python_timeout(self):
        code = "while True:\n    pass"
        result = self.executor.execute_code(code, 'python', time_limit=1)
        self.assertFalse(result['success'])
        self.assertEqual(result['status'], 'time_limit_exceeded')
        self.assertIn("Time limit exceeded", result['error'])

    def test_code_security_violations(self):
        # Test os import block
        code_os = "import os\nos.system('dir')"
        result = self.executor.execute_code(code_os, 'python')
        self.assertFalse(result['success'])
        self.assertEqual(result['status'], 'security_error')
        self.assertIn("Security Violation", result['error'])

        # Test subprocess block
        code_sub = "from subprocess import Popen"
        result = self.executor.execute_code(code_sub, 'python')
        self.assertFalse(result['success'])
        self.assertEqual(result['status'], 'security_error')

        # Test open file block
        code_open = "with open('file.txt', 'w') as f:\n    f.write('hi')"
        result = self.executor.execute_code(code_open, 'python')
        self.assertFalse(result['success'])
        self.assertEqual(result['status'], 'security_error')
