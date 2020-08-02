import json
import zipfile
from pathlib import Path
from typing import List

from PIL import Image

from wastickers import Openable, StickerPack


class InvalidWastickersFile(Exception):
    pass


def check_valid_wastickers(filepath: Openable) -> None:
    """
    Checks that input file is a valid .wastickers file.
    
    Raises InvalidWastickersFile if invalid.
    """
    try:
        # File checks
        assert Path(filepath).suffix == ".wastickers", "Extension must be .wastickers"
        assert zipfile.is_zipfile(filepath), f"{filepath} is not a zip file"

        with zipfile.ZipFile(filepath) as zf:
            namelist = zf.namelist()

            # PNG checks
            png_count = sum(name.lower().endswith(".png") for name in namelist)
            assert png_count == 1, "Must have exactly one .png file"
            assert "tray.png" in namelist, "tray.png not found"
            with zf.open("tray.png") as imgfile:
                img = Image.open(imgfile)
                assert img.format == "PNG", "tray.png must be a PNG file"
                assert img.size == (
                    96,
                    96,
                ), f"tray.png must be size 96x96 pixels [current size: {img.size}]"
                assert (
                    zf.getinfo("tray.png").file_size < 50 * 1024
                ), "tray.png must be smaller than 50KB"

            # WEBP checks
            webplist = [name for name in namelist if name.endswith(".webp")]
            webp_count = len(webplist)
            assert 1 <= webp_count <= 30, "Must have 3 to 30 .webp files"
            for webpfile in webplist:
                with zf.open(webpfile) as imgfile:
                    img = Image.open(imgfile)
                    assert img.format == "WEBP", f"{webpfile} must be a WEBP file"
                    assert img.size == (
                        512,
                        512,
                    ), f"{webpfile} must be size 512x512 pixels [current size: {img.size}]"
                    assert (
                        zf.getinfo(webpfile).file_size < 100 * 1024
                    ), f"{webpfile} must be smaller than 100KB"

            # TXT checks
            assert "title.txt" in namelist, "Must have title.txt file"
            assert "author.txt" in namelist, "Must have author.txt file"

    except AssertionError as e:
        raise InvalidWastickersFile(e)  # Silly hack


def from_wastickers(file_path: Openable) -> StickerPack:
    """Returns a StickerPack with contents from a valid .wastickers file."""
    file_path = Path(file_path)
    pack = StickerPack()

    pack.file_name = file_path.stem

    with zipfile.ZipFile(file_path) as zf:
        zip_names = zf.namelist()
        webp_names = [name for name in zip_names if name.endswith(".webp")]

        pack.author = zf.read("author.txt").decode("utf-8")
        pack.title = zf.read("title.txt").decode("utf-8")

        # Need to .load() the Image objects below, as the .open() method is lazy.
        # The images will leave the context manager, so modifying the file later
        # without calling the .load() method will result in an AttributeError.

        with zf.open("tray.png") as fp:
            pack.tray_img = Image.open(fp)
            pack.tray_img.load()

        for webp in webp_names:
            with zf.open(webp) as fp:
                img = Image.open(fp)
                img.load()
                pack.sticker_imgs[webp] = img

    return pack


def from_contents(
    folder_path: Openable, *, change_titles: dict = dict(), change_publisher: str = ""
) -> List[StickerPack]:
    """
    Convert a folder containing contents.json into multiple StickerPack's. 
    
    `folder_path` points to a folder similar to the structure mentioned in WhatsApp's
    Android sticker repository on Github. The folder should contain a contents.json
    file, and one subfolder for the assets of each sticker pack. See 
    https://github.com/WhatsApp/stickers/tree/master/Android#modifying-the-contentsjson-file
    for more details.

    This method reads the contents.json file, and creates a StickerPack object with the
    relevant metadata and images.

    To override the title of a StickerPack, provide a dict to `change_titles` where the
    keys are the old titles, and the values are the new titles. Titles not in the dict
    keep their original title.

    To change the publisher of all sticker packs, provide a string to
    `change_publisher`.
    """
    folder = Path(folder_path)
    if not folder.is_dir():
        raise ValueError(f"{folder} is not a directory.")

    with open(folder / "contents.json") as fp:
        contents: dict = json.load(fp)

    packs = []

    for sp in contents["sticker_packs"]:
        sp_folder: Path = folder / sp["identifier"]
        stickers: List[dict] = sp["stickers"]

        pack = StickerPack()

        pack.title = sp["name"]
        if pack.title in change_titles:
            pack.title = change_titles[pack.title]

        pack.author = change_publisher or sp["publisher"]

        pack.tray_img = Image.open(sp_folder / sp["tray_image_file"])
        pack.tray_img.load()

        for sticker in stickers:
            name = sticker["image_file"]
            img = Image.open(sp_folder / name)
            img.load()
            pack.sticker_imgs[name] = img

        packs.append(pack)

    return packs
