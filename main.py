from core import *
from core.logging import *
import asyncio


async def main(*args):
    args = args[0]
    argc = len(args)

    if argc == 1:
        print("Not enough arguments passed")
    else:
        # try to handle mode
        mode = args[1]
        if mode == '-s':
            # run as server
            if argc > 3:
                print("Too many arguments passed")
                exit(1)
            s_port = args[2]
            server = Server(s_port)
            await server.deploy()

        elif mode == '-c':
            # run as client

            if argc > 4:
                print("Too many arguments passed")
                exit(1)

            ts_ip, ts_port = args[2:]
            client = Client(ts_ip, ts_port)
            await client.connect()

        else:
            print(f'Unexpected mode {mode}')
            exit(1)


if __name__ == '__main__':
    import sys
    asyncio.run(main(sys.argv))
