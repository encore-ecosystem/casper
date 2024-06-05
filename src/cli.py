from src.utils import *
from src.client import VCSWS

import asyncio
import pprint
import pickle


#
# CLI
#
def run_cli(client: VCSWS):
    while True:
        match client.prompt():
            case 'init':
                client.logger(client.init, client.prompt("Enter project path: "))
                client.initialized = True

            case 'status':
                initialize_executor(
                    client.logger,
                    client.initialized,
                    client.status,
                )

            case 'sync':
                initialize_executor(
                    asyncio.run,
                    client.initialized,
                    client.sync()
                )

            case 'sub':
                initialize_executor(
                    asyncio.run,
                    client.initialized,
                    client.sub()
                )
            case 'ignore':
                initialize_executor(
                    client.logger,
                    client.initialized,
                    client.ignore, client.prompt("Enter ignore object: ")
                )
            case 'profile':
                initialize_executor(
                    client.logger,
                    client.initialized,
                    lambda: pprint.pprint(client.logger.get_profiler())
                )
            case 'exit':
                break

        # checkpoint
        if client.save:
            with open("./vcsws.pickle", "wb") as f:
                pickle.dump(client, f)