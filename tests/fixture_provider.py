"""VM-only deterministic API fixture. This is NOT a model and uses no credentials."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        # Capture only synthetic VM prompts for persistence/identity assertions.
        Path('/tmp/fixture-request.json').write_text(json.dumps(request))
        message = 'VM fixture: resident conversation works.'
        self.send_response(200)
        if request.get('stream'):
            self.send_header('Content-Type', 'text/event-stream')
            self.end_headers()
            for delta, finish in [({'role': 'assistant', 'content': message}, None), ({}, 'stop')]:
                payload = {'id': 'fixture-response', 'object': 'chat.completion.chunk', 'created': 1,
                           'model': 'fixture-model', 'choices': [{'index': 0, 'delta': delta, 'finish_reason': finish}]}
                self.wfile.write(('data: ' + json.dumps(payload) + '\n\n').encode())
            self.wfile.write(b'data: [DONE]\n\n')
        else:
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'id': 'fixture-response', 'object': 'chat.completion', 'created': 1,
                'model': 'fixture-model', 'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': message},
                'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2}}).encode())

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    HTTPServer(('127.0.0.1', 18080), Handler).serve_forever()
