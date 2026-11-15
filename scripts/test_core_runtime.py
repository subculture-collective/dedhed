import contextlib
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import core_runtime


class MaintenanceUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'runtime').mkdir()
        (self.root / 'runtime/selection.json').write_text('[{"item_id":"approved"}]')
        # The initial host receipt intentionally lags the running deployment.
        (self.root / 'core-release.json').write_text('{"version":"0.4.12"}')

    def test_monitor_follows_running_version_and_accepted_user_agent(self):
        documents = {
            '/api/ready': {'status': 'ready'},
            '/api/version': {'core_version': '0.4.13'},
            '/api/recordings': {'items': [{'recording': {'id': 'approved'}}], 'total': 1},
            '/api/station': {
                'program': {'recording_id': 'approved', 'duration': 100},
                'offset': 10, 'revision': 'preserved',
                'server_time': datetime.now(timezone.utc).isoformat(),
            },
        }

        def response(request, **_):
            self.assertEqual(request.get_header('User-agent'), 'Dedhed-public-monitor/1.0')
            path = request.full_url.removeprefix('https://dedhed.test')
            if path == '/api/audio/approved':
                result = io.BytesIO(b'a' * 4096)
                result.status = 206
                result.headers = {'Content-Range': 'bytes 0-4095/10000'}
            else:
                result = io.BytesIO(json.dumps(documents[path]).encode())
                result.status = 200
                result.headers = {}
            return result

        with patch.object(core_runtime, 'running_image', return_value='sha256:current'), \
                patch.object(core_runtime.subprocess, 'check_output', return_value='0.4.13\n'), \
                patch.object(core_runtime, 'urlopen', side_effect=response):
            result = core_runtime.monitor(self.root, 'https://dedhed.test')
        self.assertEqual(result['core_version'], '0.4.13')

    def test_replay_overrides_an_old_environment_pin_with_running_image(self):
        completed = subprocess.CompletedProcess([], 0, '{"revision":"renewed","programs":[{}]}', '')
        with patch('sys.argv', ['core_runtime.py', 'replay', '--root', str(self.root)]), \
                patch.dict(core_runtime.os.environ, {'ARCHIVE_ENGINE_IMAGE': 'old-pin'}), \
                patch.object(core_runtime, 'running_image', return_value='sha256:current'), \
                patch.object(core_runtime.subprocess, 'run', return_value=completed) as run, \
                contextlib.redirect_stdout(io.StringIO()):
            core_runtime.main()
        self.assertEqual(run.call_args.kwargs['env']['ARCHIVE_ENGINE_IMAGE'], 'sha256:current')
        self.assertIn('renew-public-audio', run.call_args.args[0])


if __name__ == '__main__':
    unittest.main()

