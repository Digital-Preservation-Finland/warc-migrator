"""
Test the WARC migrator.
"""
import os
import pytest
from warc_migrator.migrator import warc_migrator, validate


@pytest.mark.parametrize(
    ["source", "meta"],
    [
        ("valid_1.0.arc", ()),
        ("valid_1.1.arc", ()),
        ("invalid_1.0_missing_length.arc", ()),
        ("valid_0.17.warc", ()),
        ("valid_0.17_scandinavian.warc", ()),
        ("invalid_0.17_incorrectly_compressed.warc.gz", ()),
        ("valid_1.0.arc", (("k1", "v1"), ("k2", "v2"))),
        ("valid_1.1.arc", (("k1", "v1"), ("k2", "v2"))),
        ("invalid_1.0_missing_length.arc", (("k1", "v1"), ("k2", "v2"))),
        ("valid_0.17.warc", (("k1", "v1"), ("k2", "v2"))),
        ("valid_0.17_scandinavian.warc", (("k1", "v1"), ("k2", "v2"))),
        ("invalid_0.17_incorrectly_compressed.warc.gz",
         (("k1", "v1"), ("k2", "v2"))),

    ]
)
def test_warc_migrator(source, meta, testpath):
    """
    Test the main migrator.
    Will raise an exception, if the result is not valid.
    """
    target = os.path.join(testpath, "warc.warc.gz")
    source = os.path.join("tests/data", source)
    warc_migrator(source, target, meta)


def test_validate():
    """
    Validate warc file.
    """
    validate("tests/data/valid_1.0.warc.gz")
    with pytest.raises(ValueError):
        validate("tests/data/invalid_1.0.warc")
