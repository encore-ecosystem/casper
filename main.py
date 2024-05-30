from src.vcsws_core import VCSWS
import asyncio
import pickle
import os


SAVE_PROGRESS = False


def main():
    # Load last settings
    if os.path.exists("./vcsws.pickle") and SAVE_PROGRESS:
        with open("./vcsws.pickle", "rb") as f:
            vcsws = pickle.load(f)
    else:
        vcsws = VCSWS()

    while True:
        req = vcsws.prompt()
        match req:
            case 'init':
                vcsws.init(vcsws.prompt("Enter project path: "))

            case 'make_new_branch':
                vcsws.make_new_branch(vcsws.prompt("Enter branch name: "))

            case 'status':
                vcsws.status()

            case 'commit':
                vcsws.commit(
                    commit_name = vcsws.prompt("Enter commit name: "),
                    commit_description = vcsws.prompt("Enter commit description: "),
                )

            case 'pull':
                asyncio.run(
                    vcsws.pull(vcsws.prompt("Enter address: "))
                )

            case 'push':
                asyncio.run(
                    vcsws.push(vcsws.prompt("Enter address: "))
                )

            case 'branches':
                for branch in vcsws.get_branches():
                    print(f" - {branch}")

            case 'relocate':
                vcsws.relocate(vcsws.prompt("Enter target branch name:"))

            case 'deploy':
                asyncio.run(vcsws.deploy())

            case 'exit':
                break

        # checkpoint
        if SAVE_PROGRESS:
            with open("./vcsws.pickle",  "wb") as f:
                pickle.dump(vcsws, f)


if __name__ == '__main__':
    main()
