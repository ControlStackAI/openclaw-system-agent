"""VM-only deterministic API fixture. This is NOT a model and uses no credentials."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'object': 'list', 'data': [
            {'id': 'fixture-model', 'object': 'model', 'owned_by': 'local-test-fixture'}]}).encode())

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        # Capture only synthetic VM prompts for persistence/identity assertions.
        Path('/tmp/fixture-request.json').write_text(json.dumps(request))
        message = 'VM fixture: resident conversation works.'
        # OpenClaw 9.8 exposes MCP tools through Tool Search. Exercise that real
        # discovery and a read-only desktop call instead of disabling compaction.
        tools = {t['function']['name'] for t in request.get('tools', [])}
        messages = request.get('messages', [])
        probe = any(m.get('role') == 'user' and 'installed-fixture-response' in str(m.get('content', '')) for m in messages)
        probe = probe and any('desktop: hyprland' in str(m.get('content', '')) for m in messages)
        calls = {c.get('function', {}).get('name') for m in messages for c in (m.get('tool_calls') or [])}
        tool_call = None
        if probe and 'tool_search' in tools and 'tool_search' not in calls:
            tool_call = {'id': 'fixture-search', 'type': 'function', 'function': {
                'name': 'tool_search', 'arguments': json.dumps({'query': 'hypruse desktop', 'limit': 3})}}
        elif probe and 'tool_call' in tools and 'tool_search' in calls and 'tool_call' not in calls:
            tool_call = {'id': 'fixture-desktop', 'type': 'function', 'function': {
                'name': 'tool_call', 'arguments': json.dumps({'id': 'hypruse__desktop', 'args': {}})}}
        response_message = {'role': 'assistant', 'content': message}
        finish_reason = 'stop'
        if tool_call:
            response_message = {'role': 'assistant', 'tool_calls': [tool_call]}
            finish_reason = 'tool_calls'

        self.send_response(200)
        if request.get('stream'):
            self.send_header('Content-Type', 'text/event-stream')
            self.end_headers()
            delta_message = dict(response_message)
            if tool_call:
                delta_message['tool_calls'] = [dict(tool_call, index=0)]
            for delta, finish in [(delta_message, None), ({}, finish_reason)]:
                payload = {'id': 'fixture-response', 'object': 'chat.completion.chunk', 'created': 1,
                           'model': 'fixture-model', 'choices': [{'index': 0, 'delta': delta, 'finish_reason': finish}]}
                self.wfile.write(('data: ' + json.dumps(payload) + '\n\n').encode())
            self.wfile.write(b'data: [DONE]\n\n')
        else:
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'id': 'fixture-response', 'object': 'chat.completion', 'created': 1,
                'model': 'fixture-model', 'choices': [{'index': 0, 'message': response_message,
                'finish_reason': finish_reason}], 'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2}}).encode())

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    HTTPServer(('127.0.0.1', 18080), Handler).serve_forever()
