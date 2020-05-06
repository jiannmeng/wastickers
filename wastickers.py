import math
import mimetypes
import re
import shutil
import string
from pathlib import Path
from typing import Collection, NamedTuple, List, Union

import requests
from bs4 import BeautifulSoup
from PIL import Image

PathType = Union[str, Path]


class Metadata(NamedTuple):
    """Hold data from scraping store website."""

    title: str
    author: str
    image_urls: List[str]


class PackInfo(NamedTuple):
    """Hold data for creation of .wastickers pack."""

    title: str
    author: str
    image_paths: List[PathType]
    tray_path: PathType


# Commonly used paths.
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


def _is_snake_char(char: str) -> bool:
    assert len(char) == 1 and isinstance(char, str)
    return char.isdigit() or (char in string.ascii_letters) or (char in "_ .-\n")


def _to_snake_case(text: str) -> str:
    text = "".join(filter(_is_snake_char, text))
    text = text.lower()
    text = text.replace(" ", "_").replace(".", "_").replace("-", "_").replace("\n", "_")
    while "__" in text:
        text = text.replace("__", "_")
    if text[-1] == "_":
        text = text[:-1]
    return text


def get_metadata(url: str) -> Metadata:
    response = requests.get(url)
    if not response.ok:
        raise Exception(f"Request to {url} failed.")
    soup = BeautifulSoup(response.content, "html.parser")

    if "store.line.me/stickershop/product/" in url:
        # LINE sticker store.
        title = soup.find(class_="mdCMN38Item01Ttl").text
        author = soup.find(class_="mdCMN38Item01Author").text
        pattern = re.compile(
            r"https:\/\/stickershop.line-scdn.net\/stickershop\/v1\/sticker"
            r"\/\d+\/android\/sticker.png"
        )
    elif "store.line.me/emojishop/product/" in url:
        title = soup.find(class_="mdCMN08Ttl").text
        author = soup.find(class_="mdCMN08Copy").text
        pattern = re.compile(
            r"https:\/\/stickershop.line-scdn.net\/sticonshop\/v1\/sticon"
            r"\/[a-zA-Z\d]+\/iPhone\/\d+.png"
        )
    title = title.strip()
    author = author.strip()
    image_urls = sorted(set(pattern.findall(response.text)))
    return Metadata(title, author, image_urls)


def download_images(image_urls: Collection[str], dl_folder: PathType) -> None:
    """Download sticker images using `metadata` info to `dl_folder`."""
    dl_folder = Path(dl_folder)
    Path.mkdir(dl_folder, exist_ok=True)
    for num, url in enumerate(image_urls):
        response = requests.get(url)
        content_type = response.headers["content-type"]
        extension = mimetypes.guess_extension(content_type)
        if response.ok:
            with open(dl_folder / f"{num:03}{extension}", "wb") as f:
                f.write(response.content)


def preprocess(
    folder_path: PathType, title: str, author: str, tray_names: Collection[str] = None,
) -> List[PackInfo]:
    """Create PackInfo containing args for `make_pack`, with 30 images max per pack.

    Given a folder `folder_path`, divides the images into separate packs if there are
    more than 30 images. If `tray_names` is None, the first sticker in each pack is
    selected as the tray image. Otherwise, `tray_names` must have as many elements as
    there are packs (e.g. list of 2 strings if there are 40 images), and the tray image
    is the image with that name in each pack."""
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
        PackInfo(t, author, ipp, tp)
        for t, ipp, tp in zip(titles, image_pack_paths, tray_paths)
    ]


def make_pack(pack_info: PackInfo) -> None:
    """Make a .wastickers file, for Sticker Maker Studio.

    Creates metadata text files using `title` and `author`, converts `image_paths` into
    512px .webp images, and converts `tray_path` to a 96px .png image."""
    pack_name = _to_snake_case(pack_info.title)
    pack_folder = output / pack_name
    Path.mkdir(pack_folder, exist_ok=True)

    # Make 512px stickers.
    for image_path in pack_info.image_paths:
        image_path = Path(image_path)
        im = Image.open(image_path)
        im = _square(im, 512)
        im.save(pack_folder / f"{image_path.stem}.webp")

    # Make 96px tray image.
    im = Image.open(pack_info.tray_path)
    im = _square(im, 96)
    im.save(pack_folder / "tray.png")

    # Make title and author metadata files.
    with open(pack_folder / "title.txt", "w") as f:
        f.write(pack_info.title)
    with open(pack_folder / "author.txt", "w") as f:
        f.write(pack_info.author)

    # Make .wastickers file, place in output folder.
    zip_output = shutil.make_archive(pack_name, "zip", pack_folder)
    pack_path = Path(zip_output)
    pack_path.rename(pack_path.parent / output / f"{pack_path.stem}.wastickers")


def download(
    url: str,
    *,
    title: str = None,
    author: str = None,
    tray_names: Collection[str] = None,
) -> None:
    """Download stickers from a store page into a .wastickers file.

    Setting `title`, `author` and `tray_names` will override the defaults."""
    metadata = get_metadata(url)

    # Override default title and author if given.
    title = title if title else metadata.title
    author = author if author else metadata.author

    pack_name = _to_snake_case(title)
    dl_folder = downloads / pack_name
    download_images(metadata.image_urls, dl_folder)
    pack_infos = preprocess(dl_folder, title, author, tray_names)
    for pi in pack_infos:
        make_pack(pi)


def clean() -> None:
    """Remove all files in downloads and output folders."""
    _recursive_remove(downloads)
    _recursive_remove(output)


if __name__ == "__main__":
    pass
