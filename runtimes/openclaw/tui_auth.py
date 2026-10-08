"""Map the official provider prompter onto the local Ratatui UI."""
import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
from types import SimpleNamespace
from .runtime import environment
from system_agent import tui

def connect(setup, account):
    ui=tui.active
    ui.context('Connect your AI account')
    ui.busy('Connecting your provider', 'Starting the installed provider integration…', True)
    root=Path(shutil.which('openclaw')).resolve().parent.parent/'lib/openclaw'
    helper=Path(__file__).with_name('tui-auth.mjs')
    process=subprocess.Popen(['runuser','-u','controlstack-agent','--','node',str(helper),str(root),account],
        env=environment(setup.state),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
        bufsize=0,start_new_session=True,umask=0o077)
    selector=selectors.DefaultSelector();selector.register(process.stdout,selectors.EVENT_READ)
    url=''; device=None;success=False; buffer=b''
    try:
        while True:
            ui.cancelled()
            if b'\n' not in buffer:
                events=selector.select(.1)
                if not events:
                    if process.poll() is not None:break
                    continue
                chunk=os.read(process.stdout.fileno(),65536)
                if not chunk:break
                buffer+=chunk
                if b'\n' not in buffer:continue
            line,buffer=buffer.split(b'\n',1)
            try:message=json.loads(line)
            except ValueError:continue
            if message.get('controlstack')!=1:continue
            kind=message.get('kind')
            if kind in ('choose','input','confirm'):
                if kind=='choose':value=ui.choose(message['title'],message['options'])
                elif kind=='confirm':value=ui.choose(message['title'],['Yes','No'])==1
                else:value=ui.input(message['title'],True)
                process.stdin.write((json.dumps({'value':value})+'\n').encode());process.stdin.flush()
                ui.busy('Connecting your provider','Waiting for the provider…',True)
            elif kind=='url':
                url=message['url']
                ui.notes+='Open this address on your phone or other computer:\n'+url+'\n'
            elif kind=='device':
                device=message
                ui.request({'kind':'device','title':'Connect your ChatGPT account','text':'On your phone or another computer, visit the address and enter this code.\nThe code expires in '+str(message.get('expires','a few'))+' minutes.',
                            'url':url,'code':message['code'],'cancellable':True})
            elif kind=='note':
                # Notes are provider-auth instructions, never credentials.
                ui.notes+=str(message.get('text',''))+'\n'
            elif kind=='progress' and not device:
                ui.busy('Connecting your provider',str(message.get('text','')),True)
            elif kind=='done':
                success=bool(message.get('ok'))
                if not success:ui.info('Account connection needs attention',message.get('text','Please try again.'))
                break
        process.wait(timeout=10)
    finally:
        selector.close()
        if process.poll() is None:
            os.killpg(process.pid,signal.SIGTERM)
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
    return SimpleNamespace(returncode=0 if success and process.returncode==0 else 1)
