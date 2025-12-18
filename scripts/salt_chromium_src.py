#!/usr/bin/env python3
import random
import string
from pathlib import Path

FILES = [
    Path("base/build_config.h"),
    Path("base/base_export.h"),
]

def random_suffix(length=12):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))

def append_comment(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"{path} does not exist")

    comment = f"// testrandomstring-{random_suffix()}\n"

    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(comment)

    print(f"Appended comment to {path}")

def main():
    for path in FILES:
        append_comment(path)

if __name__ == "__main__":
    main()
