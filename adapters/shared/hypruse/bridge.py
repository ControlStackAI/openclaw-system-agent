"""Owner-session stdio MCP bridge. Unix socket only; no shell or arbitrary command."""
import argparse
import asyncio
import os
import pwd
import socket
import stat
import struct
import sys


async def serve(path, command, allowed_uids):
    if os.path.lexists(path):
        info = os.lstat(path)
        if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
            raise ValueError("Refusing to replace an unexpected socket path")
        os.unlink(path)
    slots = asyncio.Semaphore(4)

    async def connected(reader, writer):
        sock = writer.get_extra_info("socket")
        _, uid, _ = struct.unpack("3i", sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        if uid not in allowed_uids or slots.locked():
            writer.close()
            await writer.wait_closed()
            return
        async with slots:
            process = None
            tasks = []
            try:
                process = await asyncio.create_subprocess_exec(command, stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE, stderr=sys.stderr)

                async def copy(source, destination):
                    while data := await source.read(65536):
                        destination.write(data)
                        await destination.drain()

                tasks = [asyncio.create_task(copy(reader, process.stdin)),
                         asyncio.create_task(copy(process.stdout, writer)),
                         asyncio.create_task(process.wait())]
                await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            finally:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                if process and process.returncode is None:
                    process.terminate()
                    try:
                        await asyncio.wait_for(process.wait(), 3)
                    except asyncio.TimeoutError:
                        process.kill()
                        await process.wait()
                writer.close()
                await writer.wait_closed()

    server = await asyncio.start_unix_server(connected, path=path)
    os.chmod(path, 0o660)
    async with server:
        await server.serve_forever()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("socket")
    parser.add_argument("command")
    parser.add_argument("allowed_user")
    args = parser.parse_args()
    os.umask(0o007)
    asyncio.run(serve(args.socket, args.command, {os.getuid(), pwd.getpwnam(args.allowed_user).pw_uid}))


if __name__ == "__main__":
    main()
