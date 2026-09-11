import os
import tempfile
import unittest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from backend import main

class BackendTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        self.directory = tempfile.TemporaryDirectory()
        self.uploads = patch.object(main, 'UPLOAD_DIR', self.directory.name)
        self.uploads.start()
        main.user_credentials.clear()
    def tearDown(self):
        self.uploads.stop()
        self.directory.cleanup()
    def test_health_without_key(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(self.client.get('/').status_code, 200)
            self.assertEqual(self.client.post('/upload', files={'files': ('a.png', b'abc')}).status_code, 503)
    def test_empty_confirmation(self):
        self.assertEqual(self.client.post('/confirm', json={'events': [], 'session_id': 'missing'}).status_code, 400)
    def test_missing_session(self):
        self.assertEqual(self.client.post('/confirm', json={'events': [{'title': 'Class'}], 'session_id': '../../credentials'}).status_code, 401)
    def test_debug_route_removed(self):
        self.assertEqual(self.client.post('/test/confirm', json={}).status_code, 404)
    def test_untrusted_origin(self):
        self.assertEqual(self.client.get('/auth/google', headers={'origin': 'https://untrusted.example'}).status_code, 403)
    def test_cancelled_oauth(self):
        response = self.client.get('/auth/callback?error=access_denied&state=missing', follow_redirects=False)
        self.assertEqual(response.status_code, 307)
        self.assertIn('auth=error', response.headers['location'])
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test'})
    def test_upload_cleanup(self):
        with patch.object(main, 'extract_text_from_screenshot', return_value='schedule'), patch.object(main, 'parse_schedule', return_value=[{'title': 'Class'}]):
            response = self.client.post('/upload', files={'files': ('../../a.png', b'abc', 'image/png')})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(os.listdir(self.directory.name), [])
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test'})
    def test_unsupported_upload(self):
        self.assertEqual(self.client.post('/upload', files={'files': ('a.txt', b'abc')}).status_code, 415)
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test'})
    def test_oversize_cleanup(self):
        self.assertEqual(self.client.post('/upload', files={'files': ('a.png', b'x' * (10 * 1024 * 1024 + 1))}).status_code, 413)
        self.assertEqual(os.listdir(self.directory.name), [])
    def test_oauth_round_trip_and_replay(self):
        import json
        import time
        flow = Mock()
        flow.credentials.to_json.return_value = json.dumps({'token': 'fake', 'refresh_token': 'fake', 'token_uri': 'https://oauth2.googleapis.com/token', 'client_id': 'fake', 'client_secret': 'fake'})
        main.user_credentials['test-state'] = {'flow': flow, 'client_origin': main.FRONTEND_URL, 'created_at': time.monotonic()}
        with patch.object(main, 'save_session') as save:
            response = self.client.get('/auth/callback?code=fake&state=test-state', follow_redirects=False)
            self.assertIn('auth=success', response.headers['location'])
            save.assert_called_once()
        self.assertNotIn('test-state', main.user_credentials)
        response = self.client.get('/auth/callback?code=fake&state=test-state', follow_redirects=False)
        self.assertIn('auth=error', response.headers['location'])
        flow.fetch_token.assert_called_once_with(code='fake')
    def test_import_without_configuration(self):
        import subprocess, sys
        env = {**os.environ, 'PYTHON_DOTENV_DISABLED': '1'}
        env.pop('OPENAI_API_KEY', None)
        result = subprocess.run([sys.executable, '-c', 'import backend.main'], env=env, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())

if __name__ == '__main__':
    unittest.main()
