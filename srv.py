import argparse
import asyncio
import cowsay


clients: dict[str, asyncio.Queue] = {}
logged_clients: dict[str, str] = {}  # {ip: cow}
logged_cows: dict[str, str] = {}     # {сow: ip}
available_cows = set(cowsay.list_cows())


def remove_logged_clt(clt):
    if clt in logged_clients:
        available_cows.add(logged_clients[clt])
        del logged_cows[logged_clients[clt]]
        del logged_clients[clt]


async def process_who(clt: str):
    """Send list of logged clients."""
    await clients[clt].put(f"Logged: {' | '.join(logged_cows)}")


async def process_cows(clt: str):
    """Send list of possible cows."""
    await clients[clt].put(f"Available: {' | '.join(available_cows)}")


async def process_login(clt: str, cow_name: str):
    """Login as cow_name if possible."""
    if clt in logged_clients:
        await clients[clt].put(f"Warning: already logged as {logged_clients[clt]}, logout first")
        return

    if cow_name in available_cows:
        logged_clients[clt] = cow_name
        logged_cows[cow_name] = clt
        available_cows.remove(cow_name)
        await clients[clt].put(f"Succesfully logged as {cow_name}")
    else:
        await clients[clt].put(f"Cow {cow_name!r} is not available")


async def process_logout(clt: str):
    """Logout."""
    remove_logged_clt(clt)
    await clients[clt].put(f"Succesfully logged out")


async def process_say(clt: str, dst: str, msg: str):
    """Say clever thought to dst."""
    if clt not in logged_clients:
        await clients[clt].put(f"Error: login before chatting!")
        return
    if dst not in logged_cows:
        await clients[clt].put(f"Error: {dst} is not logged!")
        return
    
    dst_clt = logged_cows[dst]
    await clients[dst_clt].put(f"({logged_clients[clt]}, private)\n{cowsay.cowsay(msg, cow=logged_clients[clt])}")


async def process_yield(clt: str, msg: str):
    for tmp_clt in clients:
        if tmp_clt is not clt and tmp_clt in logged_clients:
            m = f"({logged_clients[clt]}, global)\n{cowsay.cowsay(msg, cow=logged_clients[clt])}"
            await clients[tmp_clt].put(m)


async def process_quit(clt: str):
    remove_logged_clt(clt)
    await clients[clt].put(f"Bye bye!")


# send and receive naming are from client's POV
async def chat(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    me = "{}:{}".format(*writer.get_extra_info("peername"))
    print(f"{me}: connected!")
    clients[me] = asyncio.Queue() # Queue of messages for clients
    send = asyncio.create_task(reader.readline())    # accept commands from clients
    receive = asyncio.create_task(clients[me].get()) # send messages to clients 

    while not reader.at_eof():
        done, pending = await asyncio.wait([send, receive], return_when=asyncio.FIRST_COMPLETED)
        for q in done:
            if q is send:       # process request
                send = asyncio.create_task(reader.readline())  # renew read command for that client       
                match q.result().decode().split():
                    case ['who']:
                        await asyncio.create_task(process_who(me))
                    case ['cows']:
                        await asyncio.create_task(process_cows(me))
                    case ['login', cow]:
                        await asyncio.create_task(process_login(me, cow))
                    case ['logout']:
                        await asyncio.create_task(process_logout(me))
                    case ['say', dst, *msg]:
                        await asyncio.create_task(process_say(me, dst, " ".join(msg)))
                    case ['yield', *msg]:
                        await asyncio.create_task(process_yield(me, " ".join(msg)))
                    case ['quit']:
                        await process_quit(me)
                        reader.feed_eof()
                        if writer.can_write_eof():
                            writer.write_eof()
                    case []:
                        pass
                    case _:
                        await clients[me].put(f"Wrong command")
            elif q is receive:  # send messaged
                receive = asyncio.create_task(clients[me].get())
                writer.write(f"{q.result()}\n".encode())
                await writer.drain()
    
    send.cancel()
    receive.cancel()
    print(f"{me}: quited!")

    if me in clients:
        remove_logged_clt(me)
        del clients[me]
        
    writer.close()
    await writer.wait_closed()


def parse_args():
    parser = argparse.ArgumentParser(description="Run server.",
                                     usage="python3 srv.py [IP] [PORT]")
    
    parser.add_argument("ip", type=str, default="0.0.0.0", nargs='?',
                        help="Server IP, default is 0.0.0.0")
    parser.add_argument("port", type=int, default=1337, nargs='?',
                        help="Server port, default is 1337")
    
    args = parser.parse_args()
    return args


async def main():
    args = parse_args()
    server = await asyncio.start_server(chat, args.ip, args.port)
    print("Started server!")
    async with server:
        await server.serve_forever()


asyncio.run(main())