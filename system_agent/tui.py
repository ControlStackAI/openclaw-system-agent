"""Ratatui presentation over the existing local setup operations.

Private socket messages carry prompts; secrets are never echoed or logged.
The unprivileged provider helper owns authentication, not this renderer.
"""
import builtins
import contextlib
import getpass
import io
import json
import os
from pathlib import Path
import select
import shutil
import socket
import subprocess
import sys

active = None

class Cancelled(Exception):
    pass

class Output(io.TextIOBase):
    def __init__(self, ui):
        self.ui = ui
    def write(self, text):
        self.ui.notes += text
        self.ui.send({'kind': 'log', 'text': text})
        return len(text)
    def flush(self):
        pass
    def isatty(self):
        return False

class Interface:
    def __init__(self, live, distro):
        self.live, self.distro = live, distro
        self.notes = ''
        self.phase = 'Welcome'
        self.sequence = 0
    def send(self, message):
        self.socket.sendall((json.dumps(message) + '\n').encode())
    def receive(self, expected=None):
        while True:
            line = self.reader.readline()
            if not line:
                raise EOFError('Interface closed')
            answer = json.loads(line)
            if answer.get('cancel'):
                raise Cancelled()
            if expected is None or answer.get('id') == expected:
                return answer.get('value')
    def request(self, message):
        self.sequence += 1
        message = {**message, 'id': self.sequence}
        self.send(message)
        return self.receive(self.sequence)
    def context(self, phase):
        self.phase = phase
        self.send({'kind': 'context', 'phase': phase, 'text': self.distro.upper() + (' · Live USB' if self.live else ' · Installed system')})
    def take_notes(self):
        notes, self.notes = self.notes, ''
        self.send({'kind': 'clear'})
        return notes.strip()
    def choose(self, question, options):
        return int(self.request({'kind':'choose', 'title':question, 'text':self.take_notes(), 'options':options}))
    def input(self, prompt='', secret=False):
        return self.request({'kind':'input','title':prompt,'text':self.take_notes(), 'secret':secret})
    def info(self, title, text=''):
        return self.request({'kind':'info','title':title,'text':text or self.take_notes()})
    def busy(self, title, text='', cancellable=False):
        self.request({'kind':'busy','title':title,'text':text,'cancellable':cancellable})
    def cancelled(self):
        if select.select([self.socket],[],[],0)[0]:
            self.receive()
    @contextlib.contextmanager
    def external(self):
        self.request({'kind':'suspend'})
        for fd, saved in enumerate(self.saved_fds): os.dup2(saved,fd)
        oldout,olderr=sys.stdout,sys.stderr
        sys.stdout,sys.stderr=self.saved_streams
        try:
            yield
        finally:
            sys.stdout,sys.stderr=oldout,olderr
            os.dup2(self.log_write,1);os.dup2(self.log_write,2)
            self.request({'kind':'resume'})
    def __enter__(self):
        global active
        binary=os.environ.get('CONTROLSTACK_TUI') or shutil.which('controlstack-tui')
        if not binary:
            raise FileNotFoundError('The packaged Ratatui interface is missing')
        self.socket, child=socket.socketpair()
        log_read,self.log_write=os.pipe()
        self.saved_fds=[os.dup(fd) for fd in range(3)]
        self.saved_streams=(sys.stdout,sys.stderr)
        self.process=subprocess.Popen([binary,str(child.fileno()),str(log_read)],pass_fds=(child.fileno(),log_read))
        child.close();os.close(log_read)
        self.reader=self.socket.makefile('rb', buffering=0)
        self.original_input,self.original_getpass=builtins.input,getpass.getpass
        builtins.input=self.input
        getpass.getpass=lambda prompt='Password: ',stream=None:self.input(prompt,True)
        sys.stdout=sys.stderr=Output(self)
        os.dup2(self.log_write,1);os.dup2(self.log_write,2)
        active=self
        self.context('Welcome')
        return self
    def __exit__(self,*args):
        global active
        active=None
        builtins.input,getpass.getpass=self.original_input,self.original_getpass
        sys.stdout,sys.stderr=self.saved_streams
        for fd,saved in enumerate(self.saved_fds):os.dup2(saved,fd);os.close(saved)
        try:self.send({'kind':'quit'})
        except OSError:pass
        self.reader.close();self.socket.close();os.close(self.log_write)
        try:self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:self.process.terminate();self.process.wait()

@contextlib.contextmanager
def external():
    if active:
        with active.external():yield
    else:yield
