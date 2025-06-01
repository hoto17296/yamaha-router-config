"""ふたつの設定ファイルを比較するスクリプト"""

import sys


def read_config(file_path: str) -> list[str]:
    with open(file_path, "rt") as f:
        lines = f.readlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <file1> <file2>")
        sys.exit(1)

    # read files
    config1, config2 = read_config(sys.argv[1]), read_config(sys.argv[2])

    # compare configs
    set1, set2 = set(config1), set(config2)
    lines = [(line, "added") for line in set2 - set1] + [(line, "removed") for line in set1 - set2]

    # print results
    for line, change_type in sorted(lines):
        if change_type == "added":
            print(f"\033[32m{line}\033[39m")  # green
        elif change_type == "removed":
            print(f"\033[31m{line}\033[39m")  # red
        else:
            print(line)
