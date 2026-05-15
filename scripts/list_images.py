from __future__ import annotations

import argparse

from bubbleid_flow.paths import iter_images


def main() -> None:
    parser = argparse.ArgumentParser(description="List supported image files recursively.")
    parser.add_argument("root", help="Root image folder")
    args = parser.parse_args()

    for path in iter_images(args.root):
        print(path)


if __name__ == "__main__":
    main()
