#!/usr/bin/env python
#
# list_repos.py: List GitHub repos for a specific language.
#
# Requires:
#   requests
#   GitHub API token at $HOME/.github_token
#
# Usage:
#   $ ./list_repos -L java > repos-java.tmp
#   $ cat repos-java.tmp
#   ReactiveX RxJava 2.x
#   elastic elasticsearch master
#   square retrofit master
#   ...
#
#   $ ./list_repos -C repos-java.tmp > repos-java.lst
#   $ cat repos-java.lst
#   ReactiveX RxJava 2.x 46ec6a6365ded7f9d96674baf40f7342d76ebdda
#   elastic elasticsearch master b1762d69b55959d87b8ddbd5eedb9b072a8f29af
#   square retrofit master b1ea7bad1fbddfe82412587a158d2aaa0b9f4241
#   ...
#
# Download the repos:
#   $ awk '{print "https://github.com/" $1 "/" $2 "/archive/" $4 ".zip"}' repos-java.lst > repos-java.urls
#   https://github.com/ReactiveX/RxJava/archive/46ec6a6365ded7f9d96674baf40f7342d76ebdda.zip
#   https://github.com/elastic/elasticsearch/archive/b1762d69b55959d87b8ddbd5eedb9b072a8f29af.zip
#   https://github.com/square/retrofit/archive/b1ea7bad1fbddfe82412587a158d2aaa0b9f4241.zip
#   ...
#   $ wget -w1 -i urls
#
# Download the wikis:
#   $ awk '{print "git clone --depth=1 https://github.com/" $1 "/" $2 ".wiki wiki/" $2 "-" $4; print "sleep 1";}' repos-java.lst | sh
#


import sys
import os.path
import logging
import json
import time
import requests
from urllib.parse import urljoin

URLBASE = 'https://api.github.com/'
with open(os.path.expanduser('~/.github_token')) as fp:
    TOKEN = fp.read().strip()
SESSION = requests.Session()

def call_api(url, wait=0.5):
    logging.debug(f'call_api: {url!r}...')
    time.sleep(wait)
    headers = { 'Authorization': f'token {TOKEN}' }
    resp = SESSION.get(url, headers=headers)
    if not resp.ok:
        logging.error(f'call_api: {resp.text!r}')
        raise IOError(resp.text)
    data = resp.json()
    resp.close()
    return data

def search_repos(language, minstars=100, perpage=100, npages=10):
    for page in range(npages):
        url = urljoin(
            URLBASE,
            f'/search/repositories?q=language:{language}+stars:>{minstars}&page={page+1}&per_page={perpage}')
        data = call_api(url)
        for item in data['items']:
            full_name = item['full_name']
            default_branch = item['default_branch']
            (user_name,_,repo_name) = full_name.partition('/')
            print(user_name, repo_name, default_branch)
        sys.stdout.flush()
    return

def list_repos(args):
    import fileinput
    for line in fileinput.input(args):
        f = line.strip().split(' ')
        (user_name, repo_name) = f[:2]
        url = urljoin(
            URLBASE,
            f'/repos/{user_name}/{repo_name}')
        repo = call_api(url)
        print(repo)
        sys.stdout.flush()
    return 0

def list_commits(args):
    import fileinput
    for line in fileinput.input(args):
        f = line.strip().split(' ')
        (user_name, repo_name, default_branch) = f[:3]
        url = urljoin(
            URLBASE,
            f'/repos/{user_name}/{repo_name}/branches/{branch_name}')
        repo = call_api(url)
        commit = repo['commit']
        sha = commit['sha']
        print(user_name, repo_name, default_branch, sha)
        sys.stdout.flush()
    return 0

def main(argv):
    import getopt
    def usage():
        print(f'usage: {argv[0]} [-d] [-n npages] [-L language] [-C] [path ...]')
        return 100
    try:
        (opts, args) = getopt.getopt(argv[1:], 'dn:L:C')
    except getopt.GetoptError:
        return usage()

    level = logging.INFO
    npages = 10
    language = None
    func = list_repos
    for (k, v) in opts:
        if k == '-d': level = logging.DEBUG
        elif k == '-n': npages = int(v)
        elif k == '-L': language = v
        elif k == '-C': func = list_commits

    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=level)

    if language is not None:
        search_repos(language, npages=npages)
    else:
        func(args)
    return 0

if __name__ == '__main__': sys.exit(main(sys.argv))
