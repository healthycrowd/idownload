import re
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
import feedparser
from imeta import ImageMetadata

from ..exceptions import ImageDownloadException


class PinterestSource:
    COMMAND = "pinterest"
    ARGS = ("username", "board", "dirpath")

    @classmethod
    def download(cls, username, board, dirpath, progressbar=None):
        url = f"https://www.pinterest.com/{username}/{board}.rss"
        feed = feedparser.parse(url)
        if not progressbar:

            @contextmanager
            def noop_progressbar(*args, **kwargs):
                yield files

            progressbar = noop_progressbar

        with progressbar(feed["items"], label="Downloading images") as bar:
            for item in bar:
                source_name = item["title"]
                source_id = re.match(
                    "^https:\/\/www\.pinterest\.com\/pin\/(\d+)\/$", item["guid"]
                ).groups()[0]
                metadata = {
                    "$version": "1.0",
                    "source_url": item["link"],
                    "source_id": source_id,
                    "source_name": source_name,
                    "access_date": int(datetime.now().timestamp()),
                    "tags": ["source:pinterest"],
                }

                image_url = re.search(
                    '<img src="(.+?)\.jpg" \/>', item["description"]
                ).groups()[0]
                image_url = image_url.replace("236x", "originals")

                suffixes = [".jpg", ".png"]
                while suffixes:
                    suffix = suffixes.pop(0)
                    try:
                        request = urllib.request.Request(f"{image_url}{suffix}")
                        data = urllib.request.urlopen(request).read()
                        image_url += suffix
                        break
                    except urllib.error.HTTPError as e:
                        if e.getcode() != 403 or not suffixes:
                            raise ImageDownloadException(image_url, e)

                dirpath = Path(dirpath)
                filepath = Path(image_url)
                (dirpath / filepath.name).write_bytes(data)
                # use to_image instead
                ImageMetadata(metadata).to_file(str(dirpath / f"{filepath.stem}.json"))
