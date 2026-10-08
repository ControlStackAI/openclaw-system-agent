#!/usr/bin/env python3
"""Run with unshare -n. Uses only fresh private state and synthetic credentials."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import selectors
import socket
import subprocess
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from runtimes.openclaw.runtime import environment
from system_agent.state import initialize

def check(runtime, mode):
    secret='sk-non-secret-synthetic-test-fixture-012345678901234567890'
    with tempfile.TemporaryDirectory(prefix='cs-tui-auth-') as directory:
        state=Path(directory);initialize(state,ROOT/'identity')
        env=environment(state);env['OPENCLAW_NIX_MODE']='0'
        args=['node']
        if mode=='chatgpt':args+=['--import',str(ROOT/'tests/device-code-hooks.mjs')]
        args += [str(ROOT/'runtimes/openclaw/tui-auth.mjs'),str(runtime/'lib/openclaw'),mode]
        child=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=env,bufsize=0,umask=0o077)
        selector=selectors.DefaultSelector();selector.register(child.stdout,selectors.EVENT_READ)
        messages=[];buffer=b'';deadline=time.monotonic()+90
        try:
            while time.monotonic()<deadline:
                if b'\n' not in buffer:
                    if not selector.select(.2):
                        if child.poll() is not None:break
                        continue
                    chunk=os.read(child.stdout.fileno(),65536)
                    if not chunk:break
                    buffer+=chunk
                    if b'\n' not in buffer:continue
                line,buffer=buffer.split(b'\n',1)
                assert secret.encode() not in line,'Secret appeared in output'
                try:m=json.loads(line)
                except ValueError:continue
                if m.get('controlstack')!=1:continue
                messages.append(m)
                if m['kind']=='input':
                    assert m['secret']
                    child.stdin.write((json.dumps({'value':secret})+'\n').encode());child.stdin.flush()
                if m['kind']=='done':break
            assert any(m.get('kind')=='done' and m.get('ok') for m in messages),messages
            assert child.wait(timeout=10)==0
            if mode=='chatgpt':
                assert any(m.get('kind')=='device' and m.get('code')=='TEST-CODE' for m in messages)
                assert any(m.get('kind')=='url' and m.get('url')=='https://auth.openai.com/codex/device' for m in messages)
            assert (state/'state/openclaw.sqlite').is_file()
            assert (state/'agents/main/agent/openclaw-agent.sqlite').is_file()
            for file in state.rglob('*.sqlite'):
                assert file.stat().st_mode & 0o077 == 0
            cfg=json.loads((state/'openclaw.json').read_text())
            assert cfg['agents']['defaults']['model']
        finally:
            selector.close()
            if child.poll() is None:
                child.kill();child.wait()
    return {'mode':mode,'passed':True,'private_state':True,'real_account':False}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('runtime',type=Path);a=p.parse_args()
    # Require a network namespace with no non-loopback interfaces.
    assert not [name for _,name in socket.if_nameindex() if name!='lo'],'Run in an empty network namespace'
    runtime=a.runtime.resolve()
    version=json.loads((runtime/'lib/openclaw/package.json').read_text())['version']
    print(json.dumps({'runtime':version,'checks':[check(runtime,m) for m in ['openai-api','chatgpt']]}))
