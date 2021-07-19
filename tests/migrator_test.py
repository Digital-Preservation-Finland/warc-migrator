"""
Test the WARC migrator.
"""
import os
import pytest

from click.testing import CliRunner

from warc_migrator.migrator import (migrate_to_warc, run_validation,
                                    ValidationError, warc_migrator_cli)


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
def test_migrate_to_warc(source, meta, real_count, tmpdir):
    """
    Test the main migrator.
    Will raise an exception, if the result is not valid.
    """
    target = str(tmpdir.mkdir("warc-migrator").join("warc.warc.gz"))
    source = os.path.join("tests/data", source)
    count = migrate_to_warc(source, target, meta)
    run_validation("warctools", target)
    run_validation("warcio", target)
    assert count == real_count
    assert os.path.isfile(target)


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


def test_migration_cli(tmpdir):
    """
    Ensure that the command line interface for migrating warcs works.

    Only the basic functionality is tested at the moment:
      - command takes an input and output paths
      - command runs successfully
      - command writes something into the output file
      - command outputs a message that corresponds to what we expect to have
        happened
    """
    outfile = tmpdir.join("out.warc.gz")
    result = CliRunner().invoke(warc_migrator_cli,
                                ["tests/data/valid_1.0.warc.gz", str(outfile)])
    assert result.exit_code == 0
    assert outfile.isfile()
    assert "Wrote the migrated warc into" in result.output
    assert "out.warc.gz with 4 records." in result.output
