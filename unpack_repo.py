#!/usr/bin/env python
##
##  unpack_repo.py - Unpack an entire repo .zip as a flat directory.
##
##  usage:
##    $ unpack_repo.py -b src -J '/test/' -A '\.java$' -R repos.lst -M srcmap.db zip/*.zip
##

import sys
import os.path
import logging
import zipfile
import hashlib
import re
import sqlite3

INVALID = re.compile(r'[^.a-zA-Z0-9]')
def getkey(path):
    h = hashlib.md5(path.encode('utf-8')).hexdigest()
    name = os.path.basename(path)
    name = INVALID.sub(lambda m:'_%04x' % ord(m.group(0)), name)
    return h+'_'+name

def unpack_repo(zippath, dstbase, pats=[], extract=False,
                maxfiles=10000, maxsize=1024*1024, srcmap=None, repo=None):
    assert (srcmap is None) == (repo is None)
    try:
        zfp = zipfile.ZipFile(zippath)
    except zipfile.BadZipFile as e:
        logging.error(f'error: {zippath}: {e}')
        return

    (commit,_) = os.path.splitext(os.path.basename(zippath))
    if repo is not None:
        (reponame,branch) = repo[commit]

    dstdir = None
    extracted = 0
    for info in zfp.infolist():
        if info.is_dir(): continue
        src = info.filename
        if '/.' in src: continue
        for (pat,ok) in pats:
            if pat.search(src):
                break
        else:
            ok = False
        if not ok: continue
        if maxsize < info.file_size:
            logging.info(f'skipped: {src!r} ({info.file_size})')
            continue
        (dir1,_,src1) = src.partition('/')
        if dstdir != dir1:
            dstdir = dir1
            if extract:
                try:
                    os.makedirs(os.path.join(dstbase, dstdir))
                except OSError:
                    pass
        dst = os.path.join(dstdir, getkey(src1))
        logging.debug(f'extract: {src1!r} -> {dst!r}')
        if srcmap is not None:
            srcmap.execute(
                'INSERT INTO SourceMap VALUES (NULL,?,?,?,?,?);',
                (dst, reponame, branch, commit, src1))
        if extract:
            try:
                with zfp.open(src, 'r') as fp:
                    with open(os.path.join(dstbase, dst), 'wb') as out:
                        while 1:
                            data = fp.read(2**16)
                            if not data: break
                            out.write(data)
                extracted += 1
            except IOError as e:
                logging.error(f'error: {zippath}/{src!r}: {e}')
            except (zipfile.BadZipFile, zipfile.zlib.error) as e:
                logging.error(f'error: {zippath}/{src!r}: {e}')
            if maxfiles <= extracted: break
    logging.info(f'extracted: {zippath}: {extracted} files.')
    return

def main(argv):
    import getopt
    def usage():
        print(f'usage: {argv[0]} [-d] [-n] [-A pat] [-J pat] [-f maxfiles] [-m maxsize] [-b dstbase] [-R repos.lst] [-M srcmap.db] [zip ...]')
        return 100
    try:
        (opts, args) = getopt.getopt(argv[1:], 'dnA:J:f:m:b:R:M:')
    except getopt.GetoptError:
        return usage()

    level = logging.INFO
    extract = True
    pats = []
    maxfiles = 10000
    maxsize = 1024*1024
    dstbase = '.'
    repomap = None
    srcmap = None
    for (k, v) in opts:
        if k == '-d': level = logging.DEBUG
        elif k == '-n': extract = False
        elif k == '-A': pats.append((re.compile(v), True))
        elif k == '-J': pats.append((re.compile(v), False))
        elif k == '-f': maxfiles = int(v)
        elif k == '-m': maxsize = int(v)
        elif k == '-b': dstbase = v
        elif k == '-R': repomap = v
        elif k == '-M':
            srcmap = sqlite3.connect(v)
            srcmap.executescript('''
CREATE TABLE IF NOT EXISTS SourceMap (
    Uid INTEGER PRIMARY KEY,
    FileName TEXT,
    RepoName TEXT,
    BranchName TEXT,
    CommitId TEXT,
    SrcPath TEXT
);
CREATE INDEX IF NOT EXISTS SourceMapIndex ON SourceMap(FileName);
''')
    if not args: return usage()
    assert (srcmap is None) == (repomap is None)

    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=level)

    repo = None
    if repomap is not None:
        repo = {}
        with open(repomap) as fp:
            for line in fp:
                (user,reponame,branch,commit) = line.strip().split(' ')
                reponame = f'{user}/{reponame}'
                repo[commit] = (reponame, branch)

    for zippath in args:
        unpack_repo(zippath, dstbase,
                    pats=pats, extract=extract,
                    maxsize=maxsize, maxfiles=maxfiles,
                    srcmap=srcmap, repo=repo)

    if srcmap is not None:
        srcmap.commit()
    return 0

if __name__ == '__main__': sys.exit(main(sys.argv))
