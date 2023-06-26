"""
Test the WARC migrator.
"""
import base64
import hashlib
import os
import pytest

from click.testing import CliRunner
from warcio.archiveiterator import ArchiveIterator

from warc_migrator.migrator import (migrate_to_warc, run_validation,
                                    ValidationError, warc_migrator_cli,
                                    is_arc, convert)


@pytest.mark.parametrize(
    ["source", "meta", "real_count"],
    [
        ("valid_1.0.arc", (), 4),
        ("valid_1.1.arc", (), 4),
        ("invalid_1.0_missing_length.arc", (), 4),
        ("valid_0.17.warc", (), 2),
        ("invalid_0.17_incorrectly_compressed.warc.gz", (), 2),
        ("valid_1.0.arc", (("k1", "v1"), ("k2", "v2")), 4),
        ("valid_1.1.arc", (("k1", "v1"), ("k2", "v2")), 4),
        ("valid_1.1.arc", (("k1", "v1"), ("k2", "v2"), ("k2", "v3")), 4),
        ("invalid_1.0_missing_length.arc", (("k1", "v1"), ("k2", "v2")), 4),
        ("valid_0.17.warc", (("k1", "v1"), ("k2", "v2")), 2),
        ("valid_0.17.warc", (("k1", "v1"), ("k2", "v2"), ("k2", "v3")), 2),
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


@pytest.mark.parametrize(
        ["test_arc", "meta"],
        [("valid_1.0.arc", ()),
         ("valid_1.1.arc", ()),
         ("valid_0.17.warc", ())]
)
def test_payload_checksum(test_arc, meta, tmpdir):
    """
    Test that the checksum of an arc/warc file stays the same in the warc file
    that results from the migration.
    """
    target = str(tmpdir.mkdir("warc-migrator").join("warc.warc.gz"))
    source = os.path.join("tests/data", test_arc)

    with open(source, "rb") as stream:
        for record in ArchiveIterator(stream):
            if record.rec_type == "response":
                sha1hash = hashlib.sha1(record.raw_stream.read())
                digest = base64.b32encode(sha1hash.digest())
                arc_digest = "sha1:" + digest.decode("utf-8")

    migrate_to_warc(source, target, meta)

    with open(target, "rb") as stream:
        for record in ArchiveIterator(stream):
            if record.rec_type == "response":
                warc_digest = record.rec_headers.get_header(
                    'WARC-Payload-Digest')

    assert arc_digest == warc_digest


def test_non_ascii_header(tmpdir):
    """
    Test that trying to migrate a warc with non-ASCII characters in its header
    will raise an exception.
    """
    target = str(tmpdir.mkdir("warc-migrator").join("warc.warc.gz"))
    source = "tests/data/invalid_0.17_scandinavian.warc"
    with pytest.raises(UnicodeEncodeError):
        migrate_to_warc(source, target, ())


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
    outfile = tmpdir / "out.warc.gz"
    result = CliRunner().invoke(warc_migrator_cli,
                                ["tests/data/valid_1.0.warc.gz", str(outfile)])
    assert result.exit_code == 0
    assert outfile.isfile()
    assert "Wrote the migrated warc into" in result.output
    assert "out.warc.gz with 4 records." in result.output


def test_migrate_to_warc_refuse_to_overwrite(tmpdir):
    """
    Ensure that the migration command won't overwrite existing files.
    """
    outfile = tmpdir / "out.warc.gz"
    outfile_content = "this should not be altered"
    outfile.write(outfile_content)

    with pytest.raises(OSError) as err:
        migrate_to_warc("tests/data/valid_1.0.warc.gz", str(outfile), {})

    assert "Target file already exists" in str(err)
    assert outfile.read() == outfile_content


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
