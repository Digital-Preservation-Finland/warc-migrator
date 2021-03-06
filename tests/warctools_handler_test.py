"""
Test Warctools handler
"""
import os
import pytest
from warc_migrator.warctools_handler import is_arc, convert


def test_is_arc():
    """
    Test whether the file is an ARC or a WARC file.
    """
    assert is_arc("tests/data/valid_1.0.arc")
    assert is_arc("tests/data/valid_1.1.arc")
    assert not is_arc("tests/data/valid_0.17.warc")


@pytest.mark.parametrize(
    ["infile", "given_count"],
    [
        ("valid_1.0.arc", 4),
        ("valid_1.1.arc", 4),
        ("invalid_1.0_missing_length.arc", 4)
    ]
)
def test_convert(infile, given_count, tmpdir):
    """
    Test conversion from ARC to WARC.
    """
    out = tmpdir.mkdir("warc-migrator").join("warc.warc.gz").open("wb")
    count = convert(os.path.join("tests/data", infile), out)
    assert count == given_count
