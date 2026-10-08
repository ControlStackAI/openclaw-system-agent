// Use the pinned official authentication flow with a Ratatui prompter.
// No credentials cross stdout; only the upstream auth store persists them.
import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline';
import {pathToFileURL} from 'node:url';
const [root, account] = process.argv.slice(2);
const emit = value => process.stdout.write(JSON.stringify({controlstack:1,...value})+'\n');
const input = readline.createInterface({input:process.stdin,terminal:false});
const pending=[];
input.on('line', line => {const fn=pending.shift();if(fn)fn(JSON.parse(line).value);});
const ask = value => new Promise(resolve=>{pending.push(resolve);emit(value);});
const progress = message => {emit({kind:'progress',text:message});return {update:text=>emit({kind:'progress',text}),stop:text=>emit({kind:'progress',text})};};
const prompter={
 intro:async text=>emit({kind:'note',text}),outro:async text=>emit({kind:'note',text}),
 note:async(text,title)=>emit({kind:'note',title,text}),
 text:async opts=>{while(true){const value=await ask({kind:'input',title:opts.message,secret:true});const problem=opts.validate?.(value);if(!problem)return value;emit({kind:'note',text:'That value was not accepted. Please try again.'});}},
 password:async opts=>await ask({kind:'input',title:opts.message,secret:true}),
 confirm:async opts=>Boolean(await ask({kind:'confirm',title:opts.message})),
 select:async opts=>{const index=await ask({kind:'choose',title:opts.message,options:opts.options.map(o=>o.label+(o.hint?' — '+o.hint:''))});return opts.options[index-1].value;},
 multiselect:async ()=>{throw new Error('This method requires an unsupported multi-selection prompt');},
 progress,
 deviceCode:async opts=>emit({kind:'device',code:opts.code,text:opts.message,expires:opts.expiresInMinutes}),
 openUrl:async url=>emit({kind:'url',url}),
};
const controller=new AbortController();process.on('SIGTERM',()=>controller.abort());
try {
 const pkg=JSON.parse(fs.readFileSync(path.join(root,'package.json')));
 if(!['2026.9.5','2026.9.9'].includes(pkg.version))throw new Error('Unqualified authentication runtime');
 const dist=path.join(root,'dist');
 const candidates=fs.readdirSync(dist).filter(n=>/^auth-[\w-]+\.mjs$/.test(n)&&/export \{ modelsAuthAddCommand,.*runModelsAuthLoginFlowForGateway/.test(fs.readFileSync(path.join(dist,n),'utf8')));
 if(candidates.length!==1)throw new Error('Pinned authentication integration is unavailable');
 const {runModelsAuthLoginFlowForGateway}=await import(pathToFileURL(path.join(dist,candidates[0])));
 const routes={'chatgpt':{provider:'openai',method:'device-code'},'openai-api':{provider:'openai',method:'api-key'},'other':{}};
 if(!Object.hasOwn(routes,account))throw new Error('Unsupported account route');
 const result=await runModelsAuthLoginFlowForGateway({...routes[account],setDefault:true,isRemote:true,signal:controller.signal,prompter,
  env:process.env,openUrl:prompter.openUrl,refreshAfterLogin:async()=>{},
  runtime:{log:()=>{},error:()=>{},exit:()=>{throw new Error('Authentication stopped');}},
 });
 if(!result.profiles?.length)throw new Error('No account was connected');
 emit({kind:'done',ok:true});
} catch(error) {
 // Provider exceptions can contain request details. Keep them out of the UI/logs.
 emit({kind:'done',ok:false,text:controller.signal.aborted?'Sign-in cancelled.':'Sign-in did not finish. Check the connection or account and try again. Your existing installation choices are kept.'});
 process.exitCode=1;
} finally {input.close();}
