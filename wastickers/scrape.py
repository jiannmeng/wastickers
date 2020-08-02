import mimetypes
import re
from io import BytesIO

from PIL import Image

from wastickers import StickerPack
import requests
from bs4 import BeautifulSoup


def from_line(url: str) -> StickerPack:
    pack = StickerPack()

    if "store.line.me/stickershop/product/" in url:
        title_class = "mdCMN38Item01Ttl"
        author_class = "mdCMN38Item01Author"
        tray_url_re = re.compile(
            r"https:\/\/stickershop.line-scdn.net\/stickershop\/v1\/product\/\d+"
            r"\/LINEStorePC\/main.png"
        )
        image_url_re = re.compile(
            r"https:\/\/stickershop.line-scdn.net\/stickershop\/v1\/sticker"
            r"\/\d+\/android\/sticker.png"
        )
    elif "store.line.me/emojishop/product/" in url:
        title_class = "mdCMN08Ttl"
        author_class = "mdCMN08Copy"
        tray_url_re = None
        image_url_re = re.compile(
            r"https:\/\/stickershop.line-scdn.net\/sticonshop\/v1\/sticon"
            r"\/[a-zA-Z\d]+\/iPhone\/\d+.png"
        )
    else:
        raise ValueError("Not a LINE Sticker or LINE Emoji url.")

    response = requests.get(url)
    if not response.ok:
        raise Exception(f"Request to {url} failed.")
    soup = BeautifulSoup(response.content, "html.parser")

    pack.title = soup.find(class_=title_class).text.strip()
    pack.author = soup.find(class_=author_class).text.strip()

    if tray_url_re:
        tray_url = image_url_re.findall(response.text)[0]
        response = requests.get(tray_url)
        content_type = response.headers["content-type"]
        extension = mimetypes.guess_extension(content_type)
        name = f"tray{extension}"
        with BytesIO() as fp:
            fp.write(response.content)
            img = Image.open(fp)
            pack.tray_img = img

    image_urls = sorted(set(image_url_re.findall(response.text)))
    for num, url in enumerate(image_urls):
        response = requests.get(url)
        content_type = response.headers["content-type"]
        extension = mimetypes.guess_extension(content_type)
        name = f"{num:03}{extension}"
        with BytesIO() as fp:
            fp.write(response.content)
            img = Image.open(fp)
            pack.sticker_imgs[name] = img

    return pack


# def get_metadata(url: str) -> Metadata:
#     response = requests.get(url)
#     if not response.ok:
#         raise Exception(f"Request to {url} failed.")
#     soup = BeautifulSoup(response.content, "html.parser")

#     if "store.line.me/stickershop/product/" in url:
#         # LINE sticker store.
#         title = soup.find(class_="mdCMN38Item01Ttl").text
#         author = soup.find(class_="mdCMN38Item01Author").text
#         pattern = re.compile(
#             r"https:\/\/stickershop.line-scdn.net\/stickershop\/v1\/sticker"
#             r"\/\d+\/android\/sticker.png"
#         )
#     elif "store.line.me/emojishop/product/" in url:
#         title = soup.find(class_="mdCMN08Ttl").text
#         author = soup.find(class_="mdCMN08Copy").text
#         pattern = re.compile(
#             r"https:\/\/stickershop.line-scdn.net\/sticonshop\/v1\/sticon"
#             r"\/[a-zA-Z\d]+\/iPhone\/\d+.png"
#         )
#     title = title.strip()
#     author = author.strip()
#     image_urls = sorted(set(pattern.findall(response.text)))
#     return Metadata(title, author, image_urls)


# def download_images(image_urls: Collection[str], dl_folder: PathType) -> None:
#     """Download sticker images using `metadata` info to `dl_folder`."""
#     dl_folder = Path(dl_folder)
#     Path.mkdir(dl_folder, exist_ok=True)
#     for num, url in enumerate(image_urls):
#         response = requests.get(url)
#         content_type = response.headers["content-type"]
#         extension = mimetypes.guess_extension(content_type)
#         if response.ok:
#             with open(dl_folder / f"{num:03}{extension}", "wb") as f:
#                 f.write(response.content)
