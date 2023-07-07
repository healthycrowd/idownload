import re
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
import feedparser
from imeta import ImageMetadata
from fnum import FnumMetadata

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
                yield args[0]

            progressbar = noop_progressbar

        with progressbar(feed["items"], label="Downloading images") as bar:
            for item in bar:
                source_name = item["title"]
                source_id = re.match(
                    "^https:\\/\\/www\\.pinterest\\.com\\/pin\\/(\\d+)\\/$",
                    item["guid"],
                ).groups()[0]
                metadata = {
                    "$version": "1.0",
                    "source_url": item["link"],
                    "source_id": source_id,
                    "source_name": source_name,
                    "access_date": int(datetime.now().timestamp()),
                    "tags": ["source:pinterest"],
                }

                url_start = re.search(
                    '<img src="(.+?)\\.jpg" \\/>', item["description"]
                ).groups()[0]
                url_start = url_start.replace("236x", "originals")

                suffixes = (".jpg", ".png")
                dirpath = Path(dirpath)
                possible_urls = list(f"{url_start}{suffix}" for suffix in suffixes)

                if any((dirpath / Path(url).name).exists() for url in possible_urls):
                    continue
                try:
                    fnum_metadata = FnumMetadata.from_file(dirpath)
                    if any(
                        fnum_metadata.contains(str(Path(url).name))
                        for url in possible_urls
                    ):
                        continue
                except FileNotFoundError:
                    pass

                while possible_urls:
                    image_url = possible_urls.pop(0)
                    try:
                        request = urllib.request.Request(image_url)
                        data = urllib.request.urlopen(request).read()
                        break
                    except urllib.error.HTTPError as e:
                        if e.getcode() != 403 or not possible_urls:
                            raise ImageDownloadException(image_url, e)

                filepath = dirpath / Path(image_url).name
                filepath.write_bytes(data)
                ImageMetadata(metadata).to_image(str(filepath))
