"""Monitor public audio and renew only the explicitly reviewed core selection."""
import argparse
from datetime import datetime
import fcntl
import json
from pathlib import Path
import subprocess
import time
from urllib.request import Request, urlopen


def monitor(root, base):
    def request(path, headers=None):
        with urlopen(Request(base.rstrip('/') + path, headers={'User-Agent': 'Dedhed-public-monitor/1.0', **(headers or {})}), timeout=15) as response:
            return response.status, response.headers, response.read(1024 * 1024)

    def get(path):
        return json.loads(request(path)[2])

    assert get('/api/ready')['status'] == 'ready', 'core not ready'
    version = get('/api/version')
    expected = json.loads((root / 'core-release.json').read_text())
    assert version['core_version'] == expected['version'], 'core version differs'
    selected = json.loads((root / 'runtime/selection.json').read_text())
    ids = {entry['item_id'] for entry in selected}
    catalog = get('/api/recordings')
    assert {entry['recording']['id'] for entry in catalog['items']} == ids
    assert catalog['total'] == len(ids)
    station = get('/api/station')
    assert station['program']['recording_id'] in ids
    assert 0 <= station['offset'] < station['program']['duration']
    assert abs(datetime.fromisoformat(station['server_time'].replace('Z', '+00:00')).timestamp() - time.time()) < 30
    for item in sorted(ids):
        status, headers, body = request('/api/audio/' + item, {'Range': 'bytes=0-4095'})
        assert status == 206 and len(body) == 4096
        assert headers.get('Content-Range', '').startswith('bytes 0-4095/')
    return {'core_version': version['core_version'], 'recordings': len(ids),
            'schedule_revision': station['revision'], 'offset': station['offset']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['monitor', 'replay'])
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--base', default='https://dedhed.subcult.tv')
    args = parser.parse_args()
    root = args.root.resolve()
    with (root / 'runtime/maintenance.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if args.action == 'monitor':
            result = monitor(root, args.base)
        else:
            process = subprocess.run([
                'docker', 'compose', '--project-name', 'dedhed-core',
                '-f', str(root / 'compose.yml'), 'run', '--rm', '--no-deps', '-T',
                'operator', 'renew-public-audio', '-collection', 'dedhed',
                '-file', '/run/selection.json', '-hours', '168',
                '-notes', 'Daily renewal of the two reviewed public pilot recordings',
            ], check=True, capture_output=True, text=True, timeout=600)
            schedule = json.loads(process.stdout)
            result = {'schedule_revision': schedule['revision'], 'programs': len(schedule['programs'])}
        print(json.dumps({'action': args.action, **result}))


if __name__ == '__main__':
    main()

