from PIL import Image
import glob
from pathlib import Path
from typing import Union
import shutil

cwd = Path.cwd()


def square(im: Image) -> Image:
    """Expands an Image to a square with transparent expanded areas."""
    x, y = im.size
    size = max(x, y)
    new_im = Image.new("RGBA", (size, size), (0, 0, 0, 1))
    new_im.paste(im, (int((size - x) / 2), int((size - y) / 2)))
    return new_im


def scale(im: Image, pixels: int) -> Image:
    """Scale an image to a given number of pixels on the longer side."""
    w, h = im.size
    ratio = pixels / max(w, h)
    w, h = round(w * ratio), round(h * ratio)
    return im.resize((w, h), Image.BICUBIC)


def wasticker(name: str, tray_filename: str, title: str, author: str):
    download_folder = cwd.joinpath("downloads", name)
    output_folder = cwd.joinpath("output", name)
    Path.mkdir(output_folder, exist_ok=True)

    # Make webp
    png = [
        x for x in download_folder.glob("*.png") if x.stem != "tray"
    ]  # ignore tray.png
    webp = list(download_folder.glob("*.webp"))
    image_paths = sorted(png + webp)
    for num, img_path in enumerate(image_paths):
        im = Image.open(img_path)
        im = scale(im, 512)
        im = square(im)
        im.save(output_folder.joinpath(f"{num:03}.webp"))

    # Make tray.png
    tray = download_folder.joinpath(tray_filename)
    im = Image.open(tray)
    im = scale(im, 96)
    im = square(im)
    im.save(output_folder.joinpath("tray.png"))

    # Make metadata
    with open(output_folder.joinpath("title.txt"), "w") as f:
        f.write(title)
    with open(output_folder.joinpath("author.txt"), "w") as f:
        f.write(author)

    # Make zip, rename to wastickers
    zip_output = shutil.make_archive(name, "zip", output_folder)
    p = Path(zip_output)
    p.rename(p.parent.joinpath(f"{p.stem}.wastickers"))


if __name__ == "__main__":
    wasticker("gudetama_1", "000.png", "Gudetama 1", "Sanrio")
    wasticker("gudetama_2", "025.png", "Gudetama 2", "Sanrio")
# make_tray("./downloads/gudetama/000.png")

# for i, filepath in enumerate(glob.iglob("stitch_and_scrump/*.png")):
#     im = Image.open(filepath)
#     im = scale(im, 512)
#     im = square(im)
#     im.save(f"{i:03}.webp", quality=92)
