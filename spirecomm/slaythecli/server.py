import asyncio

from aioconsole import ainput


class SlayTheSpireServer:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.clients = []
        self.message = None
        self.loop = None

    async def handle_client(self, reader, writer):
        # Register the client
        client = {
            "reader": reader,
            "writer": writer
        }
        self.clients.append(client)
        # Wait for messages
        await self.receive(client)

    async def receive(self, client):
        message = await client["reader"].readline()
        if not message or message == b"quit\n":
            client['writer'].close()
            self.clients.remove(client)
            return
        print(message.decode(), flush=True)
        await self.receive(client)

    async def wait_for_message(self):
        message = await ainput()
        if not message:
            return
        message = message.encode() + b"\n"
        for client in self.clients:
            client['writer'].write(message)
            await client['writer'].drain()
        await self.wait_for_message()

    def send(self, data):
        self.message.set_result(data)

    async def main(self):
        server = await asyncio.start_server(
            self.handle_client, self.ip, self.port)
        print("ready", flush=True)
        async with server:
            await server.serve_forever()

    def close_connections(self):
        for client in self.clients:
            if not client['writer']:
                continue
            client['writer'].close()
            client['writer'] = None


def main(ip, port):
    server = SlayTheSpireServer(ip=ip, port=port)
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(asyncio.gather(server.main(), server.wait_for_message()))
    except KeyboardInterrupt:
        pass
    server.close_connections()
