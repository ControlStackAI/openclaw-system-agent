// Exercise the shipped upstream device flow with synthetic responses only.
// This proves code/URL routing, not a real account login or provider reply.
import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';
import path from 'node:path';
const root = process.argv[2];
const { loginOpenAICodexDeviceCode } = await import(pathToFileURL(path.join(root, 'lib/openclaw/dist/extensions/openai/openai-chatgpt-device-code.js')));
const calls = [];
const credentials = await loginOpenAICodexDeviceCode({
  fetchFn: async (url, init) => {
    calls.push(String(url));
    assert.equal(init.method, 'POST');
    const endpoint = new URL(url).pathname;
    const bodies = {
      '/api/accounts/deviceauth/usercode': {device_auth_id: 'synthetic-device', user_code: 'ABCD-EFGH', interval: 1},
      '/api/accounts/deviceauth/token': {authorization_code: 'synthetic-code', code_verifier: 'synthetic-verifier'},
      '/oauth/token': {access_token: 'non-secret-fixture-access', refresh_token: 'non-secret-fixture-refresh', expires_in: 3600},
    };
    assert.ok(bodies[endpoint], `Unexpected request ${url}`);
    return new Response(JSON.stringify(bodies[endpoint]), {status: 200, headers: {'content-type': 'application/json'}});
  },
  onVerification: async ({verificationUrl, userCode}) => {
    assert.equal(verificationUrl, 'https://auth.openai.com/codex/device');
    assert.equal(userCode, 'ABCD-EFGH');
  },
});
assert.equal(calls.length, 3);
assert.equal(credentials.access, 'non-secret-fixture-access');
console.log('Passed: short URL, device code, poll and token exchange with synthetic responses.');
