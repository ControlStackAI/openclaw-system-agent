// Test-only device provider, used under an empty network namespace. The real
// OpenClaw login orchestration, prompter and auth-store writers still execute.
import {registerHooks} from 'node:module';
registerHooks({load(url,context,next){
 if(/\/extensions\/openai\/(?:\.setup\/)?openai-chatgpt-device-code(?:-[\w-]+)?\.(?:js|mjs)(?:\?|$)/.test(url)) return {format:'module',shortCircuit:true,source:`
 export async function loginOpenAICodexDeviceCode(p) {
  await p.onVerification({verificationUrl:'https://auth.openai.com/codex/device',userCode:'TEST-CODE',expiresInMs:600000});
  p.onProgress('Synthetic approval received');
  return {access:'synthetic-fixture-access',refresh:'synthetic-fixture-refresh',expires:4102444800000};
 }`};
 return next(url,context);
}});
