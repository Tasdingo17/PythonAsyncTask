import argparse
import asyncio
import cmd
import readline
import threading


class Communicator:
    """Class for communication with server."""
    def __init__(self, ip_srv: str, port_srv: int):
        self.ip_srv = ip_srv
        self.port_srv = port_srv
        self._clt_reqs: asyncio.Queue = None
        self._loop: asyncio.AbstractEventLoop = None

    async def chat(self):
        reader, writer = await asyncio.open_connection(self.ip_srv, self.port_srv)
        self._clt_reqs = asyncio.Queue()
        self._loop = asyncio.get_running_loop()

        receive = asyncio.create_task(reader.readline())    # TODO: separator
        send = asyncio.create_task(self._clt_reqs.get())
        while not reader.at_eof():
            done, pending = await asyncio.wait([send, receive, ], return_when=asyncio.FIRST_COMPLETED)
            for q in done:
                if q is receive:
                    receive = asyncio.create_task(reader.readline())    # TODO: separator
                    self.print_answer(q.result().decode())
                elif q is send:
                    send = asyncio.create_task(self._clt_reqs.get())
                    writer.write(f"{q.result()}\n".encode())
                    await writer.drain()

        send.cancel()
        receive.cancel()
        print("Comminucator exitting!")
        writer.close()
        await writer.wait_closed()


    # We need to call await from other synchronous thread after putting message...
    def queue_message(self, msg):
        asyncio.run_coroutine_threadsafe(self._clt_reqs.put(msg), self._loop)
        #print("Queue size:", self._clt_reqs.qsize())

    @staticmethod
    def print_answer(msg: str):
        """Print decoded msg and cli-buffer."""
        print("\n", msg, sep="", end="")
        prompt = ">>> "     # hardcoded for now
        print(f"\n{prompt}{readline.get_line_buffer()}", end="", flush=True)


class ChatClt(cmd.Cmd):
    intro = 'Welcome to the chat. Please log in. Type help or ? to list commands.\n'
    prompt = ">>> "

    def __init__(self, *args, communicator: Communicator = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.communicator: Communicator = communicator
        print("Initialized client!")

    def do_cows(self, arg):
        """Cow command. See available cows for login.
        
        Format: cows
        """
        self.communicator.queue_message("cows")

    def do_login(self, arg):
        """Login command. Try to login as cow_name.
        
        Format: login cow_name
        """
        #print(f"|{arg}|")
        self.communicator.queue_message("login " + arg)

    def do_logout(self, arg):
        """Logout command.
        
        Format: logout
        """
        self.communicator.queue_message("logout")

    def do_who(self, arg):
        """Who command. See logged users.
        
        Format: who
        """
        self.communicator.queue_message("who")

    def do_say(self, arg):
        """Say command. Send message directly to user.

        Format: say dst_name message text
        """
        self.communicator.queue_message("say " + arg)

    def do_yield(self, arg):
        """Yield command. Send broadcast message to all registred users.
        
        Format: yield message text
        """
        self.communicator.queue_message("yield " + arg)

    def do_quit(self, arg):
        """Quit command. Log out and disconnect from server.

        Format: quit
        """
        return self.do_exit(arg)

    def do_exit(self, arg):
        """Turn off client."""
        self.communicator.queue_message("quit " + arg)
        return True


def parse_args():
    parser = argparse.ArgumentParser(description="Run client.",
                                     usage="python3 clt.py [IP_SRV] [PORT_SRV]")
    
    parser.add_argument("ip_srv", type=str, default="0.0.0.0", nargs='?',
                        help="Server IP, default is 0.0.0.0")
    parser.add_argument("port_srv", type=int, default=1337, nargs='?',
                        help="Server port, default is 1337")
    
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    clt = ChatClt(communicator=Communicator(args.ip_srv, args.port_srv))
    _thread = threading.Thread(target=asyncio.run, args=(clt.communicator.chat(),))
    _thread.start()
    clt.cmdloop()

main()
