import re
import urllib.request
import urllib.error
import io
import sys
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager, redirect_stdout, redirect_stderr
from os import devnull
import feedparser
from imeta import ImageMetadata
from fnum import FnumMetadata

from ..exceptions import SourceAccessException, ImageDownloadException


stdout = io.StringIO()
stderr = io.StringIO()
try:
    with redirect_stdout(stdout), redirect_stderr(stderr):
        import nameattr
except ImportError:
    pass
except:
    nameattr_out = stdout.getvalue()
    nameattr_err = stderr.getvalue()
    print(nameattr_err, end="")
    print(nameattr_err, file=sys.stderr, end="")
nameattr_out = stdout.getvalue()
nameattr_err = stderr.getvalue()


class PinterestSource:
    COMMAND = "pinterest"
    ARGS = ("username", "board", "dirpath")

    @classmethod
    def download(cls, username, board, dirpath, with_attr=False, _progressbar=None):
        url = f"https://www.pinterest.com/{username}/{board}.rss"
        feed = feedparser.parse(url)
        if feed.status < 200 or feed.status > 299:
            raise SourceAccessException(
                f"HTTP status {feed.status} while requesting feed {url}"
            )

        if not _progressbar:

            @contextmanager
            def noop_progressbar(*args, **kwargs):
                yield args[0]

            _progressbar = noop_progressbar

        try:
            fnum_metadata = FnumMetadata.from_file(dirpath)
        except FileNotFoundError:
            fnum_metadata = None

        with _progressbar(feed["items"], label="Downloading images") as bar:
            for item in bar:
                source_name = item["title"]
                if with_attr:
                    try:
                        source_name = nameattr.from_text(source_name)
                    except:
                        print(nameattr_err, end="")
                        print(nameattr_err, file=sys.stderr, end="")
                        raise

                source_id = re.match(
                    "^https:\\/\\/www\\.pinterest\\.com\\/pin\\/(\\d+)\\/$",
                    item["guid"],
                ).groups()[0]

                metadata = {
                    "$version": "1.1",
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
                if fnum_metadata and any(
                    fnum_metadata.contains(str(Path(url).name)) for url in possible_urls
                ):
                    continue

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
                metadata["extension"] = filepath.suffix[1:]
                ImageMetadata(metadata).to_image(str(filepath))
                if fnum_metadata:
                    fnum_metadata.order.append(filepath.name)
                    fnum_metadata.originals[filepath.name] = filepath.name

        if fnum_metadata:
            fnum_metadata.to_file(dirpath)
