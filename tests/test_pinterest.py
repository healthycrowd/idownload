from tempfile import TemporaryDirectory
from pathlib import Path
import pytest
from networktest.mock import HttpApiMock, HttpApiMockEndpoint
from imeta import ImageMetadata
from fnum import number_files

from idownload.sources.pinterest import PinterestSource
from idownload.exceptions import ImageDownloadException


RSS_JPG = """
<?xml version="1.0" encoding="utf-8"?><rss xmlns:atom="http://www.w3.org/2005/Atom" version="2.0">
    <channel>
        <item>
            <title>Image title by Firstname Lastname</title>
            <link>https://testurl</link>
            <description>&lt;img src=&quot;https://i.pinimg.com/236x/testname.jpg&quot;&gt;</description>
            <pubDate>Fri, 07 Jul 2023 20:41:10 GMT</pubDate>
            <guid>https://www.pinterest.com/pin/1/</guid>
        </item>
    </channel>
</rss>
"""
SUFFIXES = ["jpg", "png"]


class PinterestMock(HttpApiMock):
    hostnames = ["www.pinterest.com"]

    endpoints = [
        HttpApiMockEndpoint(
            operation_id="rss",
            match_pattern=b"^GET /testuser/testboard.rss",
            response=lambda groups: (200, RSS_JPG),
        )
    ]


class PinimgMock(HttpApiMock):
    hostnames = ["i.pinimg.com"]

    endpoints = [
        HttpApiMockEndpoint(
            operation_id="original_jpg",
            match_pattern=b"^GET /originals/testname.jpg",
            response=lambda groups: (200, "testimage"),
        ),
        HttpApiMockEndpoint(
            operation_id="original_png",
            match_pattern=b"^GET /originals/testname.png",
            response=lambda groups: (200, "testimage"),
        ),
    ]


def assert_testfile(dirname, suffix, name="testname"):
    filepath = Path(dirname) / f"{name}{suffix}"
    expected = '"testimage"'
    actual = filepath.read_text()
    assert actual == expected

    expected = {
        "$version": "1.0",
        "source_url": "https://testurl",
        "source_id": "1",
        "source_name": "Image title by Firstname Lastname",
        "tags": ["source:pinterest"],
    }
    actual = dict(ImageMetadata.from_image(str(filepath)))
    assert int(actual["access_date"]) == actual["access_date"]
    del actual["access_date"]
    assert actual == expected


@pytest.mark.parametrize("suffix", SUFFIXES)
def test_download_success_once(suffix):
    tempdir = TemporaryDirectory()

    with PinterestMock() as mock_pinterest:
        with PinimgMock() as mock_pinimg:
            for other_suffix in SUFFIXES:
                getattr(mock_pinimg, f"original_{other_suffix}").response = (
                    (lambda groups: (200, "testimage"))
                    if other_suffix == suffix
                    else (lambda groups: (403, None))
                )
            PinterestSource.download("testuser", "testboard", tempdir.name)
            mock_pinterest.rss.request_mock.assert_called_once()
            getattr(mock_pinimg, f"original_{suffix}").request_mock.assert_called_once()

    assert_testfile(tempdir.name, f".{suffix}")


def test_download_success_ignore_filename_duplicates():
    tempdir = TemporaryDirectory()

    with PinterestMock() as mock_pinterest:
        with PinimgMock() as mock_pinimg:
            PinterestSource.download("testuser", "testboard", tempdir.name)
            mock_pinterest.rss.request_mock.assert_called_once()
            mock_pinimg.original_jpg.request_mock.assert_called_once()
    assert_testfile(tempdir.name, ".jpg")

    with PinterestMock() as mock_pinterest:
        with PinimgMock() as mock_pinimg:
            PinterestSource.download("testuser", "testboard", tempdir.name)
            mock_pinterest.rss.request_mock.assert_called_once()
            mock_pinimg.original_jpg.request_mock.assert_not_called()
    assert_testfile(tempdir.name, ".jpg")


def test_download_success_ignore_fnum_duplicates():
    tempdir = TemporaryDirectory()

    with PinterestMock() as mock_pinterest:
        with PinimgMock() as mock_pinimg:
            PinterestSource.download("testuser", "testboard", tempdir.name)
            mock_pinterest.rss.request_mock.assert_called_once()
            mock_pinimg.original_jpg.request_mock.assert_called_once()
    assert_testfile(tempdir.name, ".jpg")

    metadata = number_files(tempdir.name, SUFFIXES, include_imeta=True)
    metadata.to_file(tempdir.name)
    assert_testfile(tempdir.name, ".jpg", name="1")

    with PinterestMock() as mock_pinterest:
        with PinimgMock() as mock_pinimg:
            PinterestSource.download("testuser", "testboard", tempdir.name)
            mock_pinterest.rss.request_mock.assert_called_once()
            mock_pinimg.original_jpg.request_mock.assert_not_called()
    assert_testfile(tempdir.name, ".jpg", name="1")


def test_download_fail_imagedownload():
    tempdir = TemporaryDirectory()

    with PinterestMock() as mock_pinterest:
        with PinimgMock() as mock_pinimg:
            for suffix in SUFFIXES:
                getattr(mock_pinimg, f"original_{suffix}").response = lambda groups: (
                    403,
                    None,
                )
            with pytest.raises(ImageDownloadException):
                PinterestSource.download("testuser", "testboard", tempdir.name)
