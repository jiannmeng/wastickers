import mimetypes
import re
import sys
import os
import math
import requests
from pathlib import Path

cwd = Path.cwd()


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def download_line(url, name):
    response = requests.get(url)
    if not response.ok:
        raise Exception("oops")

    pattern = re.compile(
        r"https:\/\/stickershop.line-scdn.net\/stickershop\/v1\/sticker\/\d+\/android\/sticker.png"
    )
    results = sorted(set(pattern.findall(response.text)))

    num_folders = math.ceil(len(results) / 30)

    if num_folders == 1:
        dl_folders = [cwd.joinpath("downloads", name)]
    elif num_folders > 1:
        dl_folders = [
            cwd.joinpath("downloads", f"{name}_{x}") for x in range(1, num_folders + 1)
        ]
    for folder in dl_folders:
        Path.mkdir(folder, exist_ok=True)

    multi_results = chunks(results, math.ceil(len(results) / num_folders))

    num = 0
    for folder, results in zip(dl_folders, multi_results):
        for url in results:
            response = requests.get(url)
            content_type = response.headers["content-type"]
            extension = mimetypes.guess_extension(content_type)
            if response.ok:
                with open(f"{folder}/{num:03}{extension}", "wb") as f:
                    f.write(response.content)
                num += 1


if __name__ == "__main__":
    download_line("https://store.line.me/stickershop/product/5030/en", "gudetama")
