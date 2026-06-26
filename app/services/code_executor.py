import subprocess
import tempfile
import os
import time
import signal
import logging
from typing import Dict, List, Tuple, Any

class CodeExecutor:
    """Secure code execution service for contest submissions"""
    
    def __init__(self):
        self.supported_languages = {
            'python': {
                'extension': '.py',
                'command': ['python3', '{filename}'],
                'timeout': 5
            },
            'java': {
                'extension': '.java',
                'command': ['javac', '{filename}', '&&', 'java', '{classname}'],
                'timeout': 10
            },
            'cpp': {
                'extension': '.cpp',
                'command': ['g++', '-o', '{output}', '{filename}', '&&', '{output}'],
                'timeout': 10
            },
            'c': {
                'extension': '.c',
                'command': ['gcc', '-o', '{output}', '{filename}', '&&', '{output}'],
                'timeout': 10
            }
        }
    
    def execute_code(self, code: str, language: str, input_data: str = "", 
                    time_limit: int = 5, memory_limit: int = 256) -> Dict[str, Any]:
        """
        Execute code with input and return results
        
        Args:
            code: The source code to execute
            language: Programming language (python, java, cpp, c)
            input_data: Input to provide to the program
            time_limit: Maximum execution time in seconds
            memory_limit: Maximum memory usage in MB
            
        Returns:
            Dictionary containing execution results
        """
        if language not in self.supported_languages:
            return {
                'success': False,
                'status': 'error',
                'output': '',
                'error': f'Unsupported language: {language}',
                'execution_time': 0.0,
                'memory_used': 0
            }
        
        lang_config = self.supported_languages[language]
        
        # Create temporary directory for execution
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                return self._execute_in_sandbox(code, language, input_data, 
                                              time_limit, memory_limit, temp_dir)
            except Exception as e:
                logging.error(f"Code execution error: {e}")
                return {
                    'success': False,
                    'status': 'error',
                    'output': '',
                    'error': str(e),
                    'execution_time': 0.0,
                    'memory_used': 0
                }
    
    def _is_code_secure(self, code: str, language: str) -> Tuple[bool, str]:
        """Perform static analysis on code to prevent basic system exploitation"""
        import re
        if language == 'python':
            # Block suspicious imports and builtins
            forbidden = [
                r'\bimport\s+os\b', r'\bfrom\s+os\b',
                r'\bimport\s+subprocess\b', r'\bfrom\s+subprocess\b',
                r'\bimport\s+sys\b', r'\bfrom\s+sys\b',
                r'\bimport\s+socket\b', r'\bfrom\s+socket\b',
                r'\bimport\s+shutil\b', r'\bfrom\s+shutil\b',
                r'\bimport\s+importlib\b', r'\bfrom\s+importlib\b',
                r'\b__import__\b', r'\beval\b', r'\bexec\b',
                r'\bopen\b\s*\('
            ]
            for pattern in forbidden:
                if re.search(pattern, code):
                    return False, f"Security Violation: Forbidden statement or library pattern matched: {pattern}"
        elif language in ['cpp', 'c']:
            # Block system calls in C/C++
            forbidden = [
                r'\bsystem\s*\(', r'\bfopen\s*\(', r'\bstd::fstream\b',
                r'\bstd::ifstream\b', r'\bstd::ofstream\b', r'\b#include\s*<fstream>\b'
            ]
            for pattern in forbidden:
                if re.search(pattern, code):
                    return False, f"Security Violation: Forbidden statement or file operation matched: {pattern}"
        return True, ""

    def _run_command_safe(self, cmd: List[str], input_data: str, time_limit: int, cwd: str) -> Tuple[int, str, str, float, str]:
        """Runs a command with a timeout, capturing stdout/stderr, cross-platform"""
        import sys
        start_time = time.time()
        
        popen_args = {
            'stdin': subprocess.PIPE,
            'stdout': subprocess.PIPE,
            'stderr': subprocess.PIPE,
            'text': True,
            'cwd': cwd
        }
        
        if os.name == 'nt':
            popen_args['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_args['preexec_fn'] = os.setsid
            
        try:
            process = subprocess.Popen(cmd, **popen_args)
            try:
                stdout, stderr = process.communicate(input=input_data, timeout=time_limit)
                execution_time = time.time() - start_time
                return process.returncode, stdout, stderr, execution_time, 'success'
            except subprocess.TimeoutExpired:
                # Terminate the process group
                if os.name == 'nt':
                    try:
                        os.kill(process.pid, signal.CTRL_BREAK_EVENT)
                    except:
                        process.kill()
                else:
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    except:
                        process.kill()
                process.wait()
                return -1, '', f'Time limit exceeded ({time_limit}s)', time_limit, 'time_limit_exceeded'
        except Exception as e:
            return -1, '', str(e), time.time() - start_time, 'error'

    def _execute_in_sandbox(self, code: str, language: str, input_data: str,
                           time_limit: int, memory_limit: int, temp_dir: str) -> Dict[str, Any]:
        """Execute code in a sandboxed environment"""
        import sys
        
        # Static security check
        is_secure, sec_err = self._is_code_secure(code, language)
        if not is_secure:
            return {
                'success': False,
                'status': 'security_error',
                'output': '',
                'error': sec_err,
                'execution_time': 0.0,
                'memory_used': 0
            }
            
        lang_config = self.supported_languages[language]
        
        # Write code to file
        filename = f"solution{lang_config['extension']}"
        filepath = os.path.join(temp_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write(code)
            
        # Prepare execution command
        if language == 'python':
            python_exe = sys.executable or 'python3'
            cmd = [python_exe, filepath]
            returncode, stdout, stderr, exec_time, status = self._run_command_safe(cmd, input_data, time_limit, temp_dir)
            return {
                'success': status == 'success' and returncode == 0,
                'status': 'success' if returncode == 0 else ('runtime_error' if status == 'success' else status),
                'output': stdout.strip(),
                'error': stderr.strip(),
                'execution_time': exec_time,
                'memory_used': 0
            }
        elif language == 'java':
            classname = self._extract_java_classname(code)
            compile_cmd = ['javac', filepath]
            run_cmd = ['java', '-cp', temp_dir, classname]
            return self._execute_java(compile_cmd, run_cmd, input_data, time_limit, temp_dir)
        elif language in ['cpp', 'c']:
            output_file = os.path.join(temp_dir, 'solution')
            compiler = 'g++' if language == 'cpp' else 'gcc'
            compile_cmd = [compiler, '-o', output_file, filepath]
            run_cmd = [output_file]
            return self._execute_compiled(compile_cmd, run_cmd, input_data, time_limit, temp_dir)
        else:
            python_exe = sys.executable or 'python3'
            cmd = [python_exe, filepath]
            returncode, stdout, stderr, exec_time, status = self._run_command_safe(cmd, input_data, time_limit, temp_dir)
            return {
                'success': status == 'success' and returncode == 0,
                'status': 'success' if returncode == 0 else ('runtime_error' if status == 'success' else status),
                'output': stdout.strip(),
                'error': stderr.strip(),
                'execution_time': exec_time,
                'memory_used': 0
            }
    
    def _execute_java(self, compile_cmd: List[str], run_cmd: List[str], 
                      input_data: str, time_limit: int, temp_dir: str) -> Dict[str, Any]:
        """Execute Java code with compilation step"""
        start_time = time.time()
        
        # Compile
        ret, stdout, stderr, exec_time, status = self._run_command_safe(compile_cmd, "", 10, temp_dir)
        if ret != 0:
            return {
                'success': False,
                'status': 'compilation_error',
                'output': '',
                'error': stderr or 'Compilation timeout or error',
                'execution_time': time.time() - start_time,
                'memory_used': 0
            }
            
        # Run
        ret, stdout, stderr, exec_time, status = self._run_command_safe(run_cmd, input_data, time_limit, temp_dir)
        return {
            'success': status == 'success' and ret == 0,
            'status': 'success' if ret == 0 else ('runtime_error' if status == 'success' else status),
            'output': stdout.strip(),
            'error': stderr.strip(),
            'execution_time': exec_time,
            'memory_used': 0
        }
    
    def _execute_compiled(self, compile_cmd: List[str], run_cmd: List[str], 
                         input_data: str, time_limit: int, temp_dir: str) -> Dict[str, Any]:
        """Execute compiled languages (C/C++)"""
        return self._execute_java(compile_cmd, run_cmd, input_data, time_limit, temp_dir)
    
    def _extract_java_classname(self, code: str) -> str:
        """Extract the main class name from Java code"""
        import re
        match = re.search(r'public\s+class\s+(\w+)', code)
        return match.group(1) if match else 'Main'
    
    def run_test_cases(self, code: str, language: str, test_cases: List[Tuple[str, str]], 
                      time_limit: int = 5) -> List[Dict[str, Any]]:
        """
        Run code against multiple test cases
        
        Args:
            code: Source code
            language: Programming language
            test_cases: List of (input, expected_output) tuples
            time_limit: Time limit per test case
            
        Returns:
            List of test results
        """
        results = []
        
        for i, (input_data, expected_output) in enumerate(test_cases):
            result = self.execute_code(code, language, input_data, time_limit)
            
            if result['status'] == 'success':
                actual_output = result['output'].strip()
                expected_output = expected_output.strip()
                
                if actual_output == expected_output:
                    test_result = {
                        'test_case': i + 1,
                        'status': 'passed',
                        'input': input_data,
                        'expected': expected_output,
                        'actual': actual_output,
                        'execution_time': result['execution_time'],
                        'error': ''
                    }
                else:
                    test_result = {
                        'test_case': i + 1,
                        'status': 'failed',
                        'input': input_data,
                        'expected': expected_output,
                        'actual': actual_output,
                        'execution_time': result['execution_time'],
                        'error': 'Wrong answer'
                    }
            else:
                test_result = {
                    'test_case': i + 1,
                    'status': 'error',
                    'input': input_data,
                    'expected': expected_output,
                    'actual': '',
                    'execution_time': result['execution_time'],
                    'error': result['error']
                }
            
            results.append(test_result)
        
        return results