// Arch uses mutable owner-selected provider configuration, not NixOS runtime
// management. Keep the released JavaScript intact; verify the full artifact
// before using the upstream recipe's runtime layout and executable wrapper.
import fs from 'node:fs';
import path from 'node:path';
const root = process.env.OPENCLAW_PACKAGE_ROOT;
const metadata = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
if (metadata.name !== 'openclaw' || metadata.version !== '2026.9.9') {
  throw new Error('Unexpected OpenClaw release artifact');
}
for (const file of ['dist/index.js', 'dist/extensions/openai/openclaw.plugin.json',
                    'dist/extensions/openai/openai-chatgpt-device-code.js']) {
  if (!fs.statSync(path.join(root, file)).isFile()) throw new Error(`Missing runtime: ${file}`);
}
const acpx = JSON.parse(fs.readFileSync(path.join(process.env.OPENCLAW_BUNDLED_ACPX, 'package.json'), 'utf8'));
if (acpx.name !== '@openclaw/acpx' || acpx.version !== metadata.version) {
  throw new Error('Bundled ACPX must match the OpenClaw release');
}

// Preload the provider's native agent runtime as well as its login provider.
// Published runtime entry points and root facade aliases are retained just as
// in the official Nix plugin staging recipe; dependency resolution uses the
// complete locked npm tree rather than downloading a plugin during first use.
const modules = path.resolve(fs.realpathSync(root), '..');
for (const id of ['acpx', 'codex']) {
  const source = path.join(modules, '@openclaw', id);
  const pkg = JSON.parse(fs.readFileSync(path.join(source, 'package.json'), 'utf8'));
  if (pkg.name !== `@openclaw/${id}` || pkg.version !== metadata.version) throw new Error(`Wrong ${id} release`);
  for (const entry of pkg.openclaw.runtimeExtensions) {
    if (!entry.startsWith('./dist/') || entry.includes('..', 2) || !fs.statSync(path.join(source, entry)).isFile()) {
      throw new Error(`Invalid runtime entry: ${entry}`);
    }
  }
  for (const entry of [...pkg.openclaw.runtimeExtensions.map(x => path.basename(x)), 'register.runtime.js', 'runtime-api.js', 'setup-api.js']) {
    if (fs.existsSync(path.join(source, 'dist', entry)) && !fs.existsSync(path.join(source, entry))) {
      // 9.8 hashes plugin runtime trees and rejects symlink entries. A regular
      // ESM facade preserves the published module's own relative imports.
      const code = fs.readFileSync(path.join(source, 'dist', entry), 'utf8');
      const target = JSON.stringify(`./dist/${entry}`);
      const hasDefault = /export\s+default\b|export\s*\{[^}]*\bdefault\b/s.test(code);
      fs.writeFileSync(path.join(source, entry), `export * from ${target};\n` +
        (hasDefault ? `export { default } from ${target};\n` : ''));
    }
  }
  const destination = path.join(root, 'dist/extensions', id);
  fs.rmSync(destination, {recursive: true, force: true});
  fs.cpSync(source, destination, {recursive: true, verbatimSymlinks: true});
}
