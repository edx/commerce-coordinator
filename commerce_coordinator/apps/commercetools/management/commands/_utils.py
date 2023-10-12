import sys
from typing import Literal, Union


def yn(question: str, default: Union[Literal['y', 'n']] = "n"):
    y = "Y" if default == "y" else "y"
    n = "N" if default == "n" else "n"

    opts = f"[{y}/{n}]"

    resps = {"yes": True, "no": False, "y": True, "n": False}
    while True:
        sys.stdout.write(f"{question} {opts}? ")
        choice = input().strip().lower()

        if default is not None and len(choice) == 0:
            return default
        elif choice in resps.keys():
            return resps[choice]
        else:
            sys.stdout.write("Please choose y or n.\n")
