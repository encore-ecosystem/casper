from src.topy_core import Topy
import asyncio
import pickle
import os


SAVE_PROGRESS = False


def main():
    # Load last settings
    if os.path.exists("./vcsws.pickle") and SAVE_PROGRESS:
        with open("./vcsws.pickle", "rb") as f:
            topy = pickle.load(f)
    else:
        topy = Topy()

    while True:
        req = topy.prompt()
        match req:
            case 'init':
                topy.init(topy.prompt("Enter project path: "))

            case 'make_new_branch':
                topy.make_new_branch(topy.prompt("Enter branch name: "))

            case 'status':
                topy.status()

            case 'commit':
                topy.commit(
                    commit_name = topy.prompt("Enter commit name: "),
                    commit_description = topy.prompt("Enter commit description: "),
                )

            case 'pull':
                asyncio.run(
                    topy.pull(topy.prompt("Enter address: "))
                )

            case 'push':
                asyncio.run(
                    topy.push(topy.prompt("Enter address: "))
                )

            case 'branches':
                for branch in topy.get_branches():
                    print(f" - {branch}")

            case 'relocate':
                topy.relocate(topy.prompt("Enter target branch name:"))

            case 'deploy':
                asyncio.run(topy.deploy())

            case 'exit':
                break

        # checkpoint
        if SAVE_PROGRESS:
            with open("./vcsws.pickle",  "wb") as f:
                pickle.dump(topy, f)



if __name__ == '__main__':
    main()
