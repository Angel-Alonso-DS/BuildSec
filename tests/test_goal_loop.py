import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MOD = Path(__file__).resolve().parents[1]/'scripts'/'goal_loop.py'
spec = importlib.util.spec_from_file_location('goal_loop',MOD)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class RunnerTests(unittest.TestCase):
    def test_check_configuration(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'checks.json'
            f.write_text(json.dumps({'checks':[{'name':'unit','argv':['python','-V'],'timeout_seconds':5}]}))
            self.assertEqual(len(module.load_checks(f)),1)
    def test_invalid_check_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'checks.json'
            f.write_text('{"checks":[{"argv":"echo hello"}]}')
            with self.assertRaises(ValueError): module.load_checks(f)
    def test_redact(self):
        self.assertNotIn('abc123',module.redact('token=abc123'))
    def test_successful_process(self):
        result=module.process(['python','-c','print(1)'],3,Path('.'))
        self.assertEqual(result['status'],'passed')
    def test_failed_process(self):
        result=module.process(['python','-c','raise SystemExit(4)'],3,Path('.'))
        self.assertEqual(result['status'],'failed')
