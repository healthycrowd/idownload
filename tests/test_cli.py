from unittest.mock import patch
from click.testing import CliRunner
import pytest

from idownload.cli import cli


def test_cli_success():
    runner = CliRunner()
    result = runner.invoke(cli, [])
    assert result.exit_code == 0


def test_command_success():
    runner = CliRunner()
    with patch("idownload.sources.pinterest.PinterestSource.download") as mock_download:
        result = runner.invoke(cli, ["pinterest", "testuser", "testboard", "testdir"])
        mock_download.assert_called_once()
    assert result.exit_code == 0


def test_command_fail():
    runner = CliRunner()
    with patch("idownload.sources.pinterest.PinterestSource.download") as mock_download:
        mock_download.side_effect = Exception()
        result = runner.invoke(cli, ["pinterest", "testuser", "testboard", "testdir"])
        mock_download.assert_called_once()
    assert result.exit_code == 1
