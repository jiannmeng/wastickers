import math
import mimetypes
import re
import shutil
from pathlib import Path
from typing import Collection, Union

import requests
from PIL import Image

PathType = Union[str, Path]
cwd = Path.cwd()  # Current working directory
downloads = cwd / "downloads"
output = cwd / "output"


def _chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def _square(im: Image, pixels: int) -> Image:
    """Transform `im` to a square with side length `pixels` and transparent padding."""
    w, h = im.size
    ratio = pixels / max(w, h)
    w, h = round(w * ratio), round(h * ratio)
    im = im.resize((w, h), Image.BICUBIC)

    size = max(w, h)
    new_im = Image.new("RGBA", (size, size), (0, 0, 0, 1))
    new_im.paste(im, (int((size - w) / 2), int((size - h) / 2)))
    return new_im


def _recursive_remove(path: PathType, inner=False) -> None:
    """Remove everything inside directory `dir`, except .gitkeep files."""
    path = Path(path)
    if path.name == ".gitkeep":
        return
    elif path.is_file():
        path.unlink()
    elif path.is_dir():
        for child in path.iterdir():
            _recursive_remove(child, inner=True)
        if inner:
            path.rmdir()


def _to_snake_case(text: str) -> str:
    """Turns a string into snake case.

    Lower case the string, then replace spaces and dashes with underscores."""
    return text.lower().replace(" ", "_").replace("-", "_")


def download(url: str, dl_folder: PathType) -> None:
    """Download stickers from LINE store to `dl_folder`."""
    dl_folder = Path(dl_folder)
    Path.mkdir(dl_folder, exist_ok=True)

    response = requests.get(url)
    if not response.ok:
        raise Exception(f"Request to {url} failed.")

    pattern = re.compile(
        r"https:\/\/stickershop.line-scdn.net\/stickershop\/v1\/sticker\/\d+\/android\/sticker.png"
    )
    results = sorted(set(pattern.findall(response.text)))

    for num, url in enumerate(results):
        response = requests.get(url)
        content_type = response.headers["content-type"]
        extension = mimetypes.guess_extension(content_type)
        if response.ok:
            with open(dl_folder / f"{num:03}{extension}", "wb") as f:
                f.write(response.content)


def preprocess(
    folder_path: PathType, title: str, author: str, tray_names: Collection[str] = None,
):
    """Create dict containing args for `make_pack`, with 30 images maximum per pack."""
    folder = Path(folder_path)
    png = [x for x in folder.glob("*.png") if x.stem != "tray"]
    webp = list(folder.glob("*.webp"))
    image_paths = sorted(png + webp)

    num_chunks = math.ceil(len(image_paths) / 30)
    chunk_size = math.ceil(len(image_paths) / num_chunks)

    if num_chunks == 1:
        titles = [title]
    elif num_chunks > 1:
        titles = [f"{title} {x+1}" for x in range(num_chunks)]
    image_pack_paths = list(_chunks(image_paths, chunk_size))
    if tray_names is None:
        tray_paths = [x[0] for x in image_pack_paths]
    elif len(tray_names) == num_chunks:
        try:
            tray_paths = [sorted(folder.glob(f"*{x}*"))[0] for x in tray_names]
        except IndexError:
            raise IndexError(f"Tray image not found.")
    else:
        raise ValueError(
            "`tray_names` must contain as many names as chunks. "
            "Each 30 images is one chunk."
        )

    return [
        {"title": t, "author": author, "image_paths": ipp, "tray_path": tp}
        for t, ipp, tp in zip(titles, image_pack_paths, tray_paths)
    ]


def make_pack(
    title: str, author: str, image_paths: Collection[PathType], tray_path: str,
) -> None:
    """Turns given arguments into a .wastickers file, for Sticker Maker Studio.

    Creates metadata text files using `title` and `author`, converts `image_paths` into
    512px .webp images, and converts `tray_path` to a 96px .png image."""
    pack_name = _to_snake_case(title)
    pack_folder = output / pack_name
    Path.mkdir(pack_folder, exist_ok=True)

    # Make 512px stickers.
    for image_path in image_paths:
        image_path = Path(image_path)
        im = Image.open(image_path)
        im = _square(im, 512)
        im.save(pack_folder / f"{image_path.stem}.webp")

    # Make 96px tray image.
    im = Image.open(tray_path)
    im = _square(im, 96)
    im.save(pack_folder / "tray.png")

    # Make title and author metadata files.
    with open(pack_folder / "title.txt", "w") as f:
        f.write(title)
    with open(pack_folder / "author.txt", "w") as f:
        f.write(author)

    # Make .wastickers file, place in output folder.
    zip_output = shutil.make_archive(pack_name, "zip", pack_folder)
    pack_path = Path(zip_output)
    pack_path.rename(pack_path.parent / output / f"{pack_path.stem}.wastickers")


def scrape(title: str, author: str, url: str) -> None:
    """Scrape a given `url` into a .wastickers file with the given metadata."""
    pack_name = _to_snake_case(title)
    dest_folder = downloads / pack_name
    download(url, dest_folder)
    pack_info = preprocess(dest_folder, title, author)
    for p in pack_info:
        make_pack(**p)


def clean() -> None:
    """Remove all files in downloads and output folders."""
    _recursive_remove(downloads)
    _recursive_remove(output)


if __name__ == "__main__":
    pass
