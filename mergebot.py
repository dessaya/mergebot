#!/usr/bin/env python3
from urllib.request import Request, urlopen
import json
import pprint
import sys
import itertools
import time
import os
import re
import platform

def display(s):
    if platform.system() == 'Darwin':
        os.system(f"""osascript -e 'display notification "{s}" with title "Mergebot"'""")

def log(s, color, notify=False):
    print(color + s + '\033[0m')
    if notify:
        display(s)

def ok(s, notify=False):
    log(s, '\033[0;32m', notify)

def error(s, notify=False):
    log(s, '\033[0;31m', notify)

def warn(s, notify=False):
    log(s, '\033[0;33m', notify)

def info(s, notify=False):
    log(s, '\033[0m', notify)

def debug(s, notify=False):
    log(s, '\033[0;30;1m', notify)

def parse_github_url(github_url):
    m = re.match(r'^https://([^/]+)/([^/]+)/([^/]+)/pull/(\d+)/?$', github_url)
    if not m:
        raise ValueError()
    domain = m.group(1)
    repo = f"{m.group(2)}/{m.group(3)}"
    pr = m.group(4)
    return domain, repo, pr

try:
    github_url = sys.argv[1]
    DOMAIN, REPO, PR = parse_github_url(github_url)
except (IndexError, ValueError):
    error(f'usage: {sys.argv[0]} <pull request url>')
    info(f'    example: {sys.argv[0]} https://github.com/owner/repo/pull/1234')
    sys.exit(1)

try:
    GITHUB_ACCESS_TOKEN = os.environ['GITHUB_ACCESS_TOKEN']
except KeyError:
    error('GITHUB_ACCESS_TOKEN environment variable missing.')
    info(f'Create your Personal Access Token (with permissions [read:user,repo]) at https://{DOMAIN}/settings/tokens')
    info(f'Then: GITHUB_ACCESS_TOKEN="..." {" ".join(sys.argv)}')
    sys.exit(1)

def request(path, data=None, method='GET'):
    url = f"https://{DOMAIN}/api/v3{path}"
    debug(f"{method} {url}")
    response = urlopen(Request(
        url,
        headers={
            'Authorization': f'token {GITHUB_ACCESS_TOKEN}',
            'Content-Type': 'application/json',
        },
        data=data,
        method=method,
    ))
    return json.loads(response.read().decode('utf-8'))

def pull_get(path):
    return request(f"/repos/{REPO}/pulls/{PR}{path}")

def statuses_get(sha):
    return request(f"/repos/{REPO}/statuses/{sha}")

def merge(commit_title, sha):
    return request(
        f"/repos/{REPO}/pulls/{PR}/merge",
        data=json.dumps({
            'commit_title': commit_title,
            'sha': sha,
            'commit_message': '',
            'merge_method': 'squash',
        }),
        method='PUT'
    )

user = request('/user')['login']
info(f'Logged in as {user}')

while True:
    info('Getting PR info...')
    pr = pull_get('')
    author = pr['user']['login']
    branch = pr['head']['ref']
    sha = pr['head']['sha']
    state = pr['state']
    mergeable = pr['mergeable']
    mergeable_state = pr['mergeable_state']
    approvers = [r['user']['login'] for r in pull_get('/reviews') if r['state'] == 'APPROVED']

    info(f"author: {author}")
    info(f"branch: {branch}")
    info(f"state: {state}")
    info(f"mergeable: {mergeable}")
    info(f"mergeable_state: {mergeable_state}")
    info(f"approvers: {approvers}")

    if author != user:
        error(f'You are not logged in as PR author ({author} != {user}). Mergebot out.', True)
        break

    if state == 'closed':
        error('PR is closed')
        break

    statuses = statuses_get(sha)
    grouped_statuses = dict(
        (k, list(v))
        for k, v in itertools.groupby(
            sorted(
                statuses,
                key=lambda s: s['state'],
            ),
            lambda s: s['state'],
        )
    )
    failures = grouped_statuses.get('error', []) + grouped_statuses.get('failure', [])
    if len(failures) > 0:
        warn("Some checks were not successful", True)
        for f in failures:
            warn(f"    {f['context']} ({f['target_url']})")

    if mergeable_state == 'dirty':
        error('You have merge conflicts!', True)

    title = f'Merge {branch} [ok:{"+".join((approvers + ["mergebot"])[:2])}]'
    info(f'Merge commit title will be: {title} ...')
    if mergeable:
        ok(f'PR is mergeable!')
        info(f'Merging now...')
        r = merge(commit_title=title, sha=sha)
        if r.get('merged', False) is True:
            ok("PR has been merged. Have a nice day!", True)
        else:
            error("Could not merge PR", True)
            error(pprint.pformat(r))
        break

    info('PR is not mergeable yet. Will check again in 5m.')
    time.sleep(300)
    print()
