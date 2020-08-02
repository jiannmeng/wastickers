import os
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Optional, Union

from PIL import Image

Openable = Union[str, Path]


class InvalidStickerPack(Exception):
    pass


class StickerPack:
    def __init__(self):
        self.file_name: str = ""
        self.title: str = ""
        self.author: str = ""
        self.tray_img: Optional[Image.Image] = None
        self.sticker_imgs: dict[str, Image.Image] = dict()

    def save(
        self, file_name: str = None, folder: Openable = None, overwrite: bool = False
    ) -> None:
        """
        Save the StickerPack to a .wastickers file on disk.

        The tray image is resized to 96x96 pixels and saved as a PNG. The stickers are 
        resized to 512x512 pixels and saved as WEBP. This modifies `self.tray_img` and 
        `self.sticker_imgs` in-place.

        The output file name is `file_name` (if given; else it uses `self.file_name` if 
        it exists; else it uses `self.title`), with extension .wastickers added on.

        The output file is saved in `folder` (if given; else defaults to the current 
        working directory).

        If the file already exists, raise a FileExistsError if `overwrite` is False, or 
        overwrite the existing file if `overwrite` is True.
        """
        self.check()  # Check that `self` is ready to be written as a .wasticker
        file_name = file_name or self.file_name or self.title
        file_path = Path(file_name + ".wastickers")
        folder = folder or os.getcwd()
        folder = Path(folder)

        # If no tray image, pick the first sticker image.
        if self.tray_img is None:
            self.tray_img = list(self.sticker_imgs.values())[0]

        mode = "w" if overwrite else "x"
        with zipfile.ZipFile(folder / file_path, mode) as zf:
            zf.writestr("title.txt", self.title)
            zf.writestr("author.txt", self.author)

            # writestr() allows us to write bytes objects to the zipfile.
            # getvalue() turns a BytesIO object to a bytes object.

            self.tray_img = _squarify(self.tray_img, 96)
            with BytesIO() as fp:
                self.tray_img.save(fp, format="PNG")
                zf.writestr("tray.png", fp.getvalue())

            for name, img in self.sticker_imgs.items():
                img = _squarify(img, 512)
                with BytesIO() as fp:
                    img.save(fp, format="WEBP")
                    zf.writestr(name, fp.getvalue())

    def check(self):
        """
        Checks that `self` can be saved as a .wastickers file.
        
        Raises InvalidStickerPack if invalid.
        """
        if not self.title:
            raise InvalidStickerPack("Missing title.")

        if not self.author:
            raise InvalidStickerPack("Missing author.")

        count = len(self.sticker_imgs)
        if not 3 <= count <= 30:
            raise InvalidStickerPack(
                f"Must have 3 to 30 sticker images. Current count: {count}."
            )


def _squarify(im: Image.Image, pixels: int) -> Image.Image:
    """Transform `im` to a square with side length `pixels` and transparent padding."""
    w, h = im.size
    ratio = pixels / max(w, h)
    w, h = round(w * ratio), round(h * ratio)
    im = im.resize((w, h), Image.BICUBIC)

    size = max(w, h)
    new_im = Image.new("RGBA", (size, size), (0, 0, 0, 1))
    new_im.paste(im, (int((size - w) / 2), int((size - h) / 2)))
    return new_im


if __name__ == "__main__":
    pass
