import asyncio
import importlib.util
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from runtimes.openclaw.runtime import local_policy, sync_installed_mcp
from system_agent.state import initialize

spec = importlib.util.spec_from_file_location("desktop_bridge", Path(__file__).parents[1] / "adapters/nixos/hypruse/bridge.py")
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class DesktopBridge(unittest.IsolatedAsyncioTestCase):
    async def exercise(self, allowed):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "mcp.sock")
            task = asyncio.create_task(bridge.serve(path, shutil.which("cat"), allowed))
            try:
                for _ in range(100):
                    if Path(path).exists():
                        break
                    await asyncio.sleep(0.01)
                self.assertEqual(Path(path).stat().st_mode & 0o777, 0o660)
                reader, writer = await asyncio.open_unix_connection(path)
                try:
                    if os.getuid() in allowed:
                        writer.write(b'{"jsonrpc":"2.0","id":1}\n')
                        await writer.drain()
                        self.assertEqual(await asyncio.wait_for(reader.readline(), 2), b'{"jsonrpc":"2.0","id":1}\n')
                    else:
                        self.assertEqual(await asyncio.wait_for(reader.read(), 2), b"")
                finally:
                    writer.close()
                    await writer.wait_closed()
                    await asyncio.sleep(0.05)
            finally:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

    async def test_owner_stream_is_forwarded(self):
        await self.exercise({os.getuid()})

    async def test_unlisted_peer_is_rejected(self):
        await self.exercise(set())

    async def test_regular_file_is_never_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mcp.sock"
            path.write_text("preserve")
            with self.assertRaises(ValueError):
                await bridge.serve(str(path), shutil.which("cat"), {os.getuid()})
            self.assertEqual(path.read_text(), "preserve")


class DesktopPolicy(unittest.TestCase):
    def test_onboarding_retains_desktop_mcp_and_restores_its_tool_access(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "state"
            initialize(state, root / "empty-identity")
            definition = {"hypruse": {"command": "/nix/store/fixture/bin/bridge", "transport": "stdio", "enabled": True}}
            path = root / "desktop-mcp.json"
            path.write_text(json.dumps(definition))
            local_policy(state, installed_mcp_path=path)
            config = json.loads((state / "openclaw.json").read_text())
            self.assertEqual(config["mcp"]["servers"], definition)
            self.assertIn("hypruse__*", config["tools"]["allow"])
            self.assertFalse(config["tools"]["elevated"]["enabled"])
            local_policy(state, installed_mcp_path=path)
            self.assertEqual(json.loads((state / "openclaw.json").read_text())["tools"]["allow"].count("hypruse__*"), 1)

    def test_reboot_sync_preserves_provider_and_removes_disabled_managed_servers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "state"
            initialize(state, root / "empty-identity")
            config_path = state / "openclaw.json"
            config = json.loads(config_path.read_text())
            config["models"] = {"fixture": "preserve-provider"}
            config["mcp"] = {"servers": {"other": {"command": "keep"}, "hypruse": {"command": "old"}}}
            config["tools"]["allow"] = ["read", "hypruse__*"]
            config_path.write_text(json.dumps(config))
            contract = root / "installed-mcp.json"
            contract.write_text(json.dumps({"nixos": {"command": "new-pinned-server"}}))
            sync_installed_mcp(state, contract=contract)
            result = json.loads(config_path.read_text())
            self.assertEqual(result["models"], config["models"])
            self.assertEqual(set(result["mcp"]["servers"]), {"other", "nixos"})
            self.assertEqual(result["tools"]["allow"], ["read", "nixos__*"])
            self.assertEqual(config_path.stat().st_mode & 0o777, 0o600)
