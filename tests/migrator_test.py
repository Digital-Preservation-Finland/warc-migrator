"""
Test the WARC migrator.
"""
import os
import pytest
from warc_migrator.migrator import (migrator, run_validation,
                                    ValidationError)


@pytest.mark.parametrize(
    ["source", "meta", "real_count"],
    [
        ("valid_1.0.arc", (), 4),
        ("valid_1.1.arc", (), 4),
        ("invalid_1.0_missing_length.arc", (), 4),
        ("valid_0.17.warc", (), 2),
        ("valid_0.17_scandinavian.warc", (), 2),
        ("invalid_0.17_incorrectly_compressed.warc.gz", (), 2),
        ("valid_1.0.arc", (("k1", "v1"), ("k2", "v2")), 4),
        ("valid_1.1.arc", (("k1", "v1"), ("k2", "v2")), 4),
        ("invalid_1.0_missing_length.arc", (("k1", "v1"), ("k2", "v2")), 4),
        ("valid_0.17.warc", (("k1", "v1"), ("k2", "v2")), 2),
        ("valid_0.17_scandinavian.warc", (("k1", "v1"), ("k2", "v2")), 2),
        ("invalid_0.17_incorrectly_compressed.warc.gz",
         (("k1", "v1"), ("k2", "v2")), 2),

    ]
)
def test_migrator(source, meta, real_count, tmpdir):
    """
    Test the main migrator.
    Will raise an exception, if the result is not valid.
    """
    target = str(tmpdir.mkdir("warc-migrator").join("warc.warc.gz"))
    source = os.path.join("tests/data", source)
    count = migrator(source, target, meta)
    assert count == real_count


def test_run_validation():
    """
    Test warc file validation.
    """
    run_validation("warctools", "tests/data/valid_1.0.warc.gz")
    run_validation("warcio", "tests/data/valid_1.0.warc.gz")
    with pytest.raises(ValidationError):
        run_validation("warctools", "tests/data/invalid_1.0.warc")
    with pytest.raises(ValidationError):
        run_validation("warcio", "tests/data/invalid_1.0.warc")
