"""
Test WARC fixing methods
"""
import os
import pytest
from warcio.statusandheaders import StatusAndHeaders
from warcio.archiveiterator import ArchiveIterator
from warc_migrator.warc_fixer import WarcFixer


@pytest.mark.parametrize(
    ["infile", "arc_data", "given_count"],
    [
        ("valid_0.17.warc", False, 2),
        ("valid_0.17_scandinavian.warc", False, 2),
        ("valid_1.0_warctools_resulted.warc", True, 4)
    ]
)
def test_fix_warc(infile, arc_data, given_count, testpath):
    """
    Test warc fixing.
    """
    infile_path = os.path.join("tests/data", infile)
    result_file = os.path.join(testpath, "warc.warc.gz")
    given_warcinfo = {"info1": "infovalue1", "info2": "infovalue2"}
    warc_fixer = WarcFixer(given_warcinfo, "warc.warc.gz")
    with open(infile_path, "rb") as filein:
        with open(result_file, "wb") as out:
            count = warc_fixer.fix_warc(filein, out, arc_data)
    assert count == given_count
    assert warc_fixer.target.warcinfo["info1"] == "infovalue1"
    assert warc_fixer.target.warcinfo["info2"] == "infovalue2"
    assert warc_fixer.target.warcinfo["conformsTo"] == \
        "https://iipc.github.io/warc-specifications/specifications/" \
        "warc-format/warc-1.0/"
    assert warc_fixer.target.warcinfo["format"] == "WARC File Format 1.0"
    assert len(warc_fixer.target.warcinfo) == 10
    assert ("WARC-Filename", "warc.warc.gz") in \
        warc_fixer.target.warcinfo_record.rec_headers.headers
    found = False
    for head in warc_fixer.target.warcinfo_record.rec_headers.headers:
        if "WARC-Date" in head:
            found = True
    assert found


def test_fix_warcinfo():
    """
    Test fixing warcinfo to meet WARC 1.0 specifications.
    """
    header = StatusAndHeaders(
        "200 OK", [("field1", "value1"), ("field2", "value2")])
    given_warcinfo = {"info1": "infovalue1", "info2": "infovalue2"}
    warc_fixer = WarcFixer(given_warcinfo, "test.warc.gz")
    warc_fixer.source.set_warcinfo(given_warcinfo)
    warc_fixer.source.create_info_record(header, "warcinfo")
    warc_fixer._fix_warcinfo()
    assert warc_fixer.target.warcinfo_record.rec_headers == header
    assert warc_fixer.target.warcinfo["info1"] == "infovalue1"
    assert warc_fixer.target.warcinfo["info2"] == "infovalue2"
    assert warc_fixer.target.warcinfo["conformsTo"] == \
        "https://iipc.github.io/warc-specifications/specifications/" \
        "warc-format/warc-1.0/"
    assert warc_fixer.target.warcinfo["format"] == "WARC File Format 1.0"
    assert len(warc_fixer.target.warcinfo) == 4
    assert ("WARC-Filename", "test.warc.gz") in \
        warc_fixer.target.warcinfo_record.rec_headers.headers
    found = False
    for head in warc_fixer.target.warcinfo_record.rec_headers.headers:
        if "WARC-Date" in head:
            found = True
    assert found


def test_fix_metadata():
    """
    Test fixing metadata to meet WARC 1.0 specifications.
    """
    header = StatusAndHeaders(
        "200 OK", [("field1", "value1"), ("field2", "value2")])
    warc_fixer = WarcFixer({}, "test.warc.gz")
    warc_fixer.source.metadata = b"Test metadata"
    warc_fixer.source.create_info_record(header, "metadata")
    warc_fixer._fix_metadata()
    assert warc_fixer.target.metadata_record.rec_headers == header
    assert warc_fixer.target.metadata == b"Test metadata"
    assert warc_fixer.target.metadata_record.content_type == \
        "application/x-internet-archive"
    assert warc_fixer.target.metadata_record.rec_headers.protocol == \
        "WARC/1.0"


def test_extract_warcinfo():
    """
    Test extracting warcinfo from a WARC 0.17 file.
    """
    header = StatusAndHeaders(
        "200 OK", [("field1", "value1"), ("field2", "value2")])
    given_warcinfo = {"info1": "infovalue1", "info2": "infovalue2"}
    warc_fixer = WarcFixer(given_warcinfo, "test.warc.gz")
    warc_fixer.source.set_warcinfo(given_warcinfo)
    with open("tests/data/valid_0.17.warc") as warc_file:
        record = ArchiveIterator(warc_file).next()
    warc_fixer.source.set_warcinfo_record(record)
    warc_fixer._extract_warcinfo()
    assert warc_fixer.source.warcinfo["info1"] == "infovalue1"
    assert warc_fixer.source.warcinfo["info2"] == "infovalue2"
    assert warc_fixer.source.warcinfo["description"] == \
        " Test description\r\n"
    assert warc_fixer.source.warcinfo["format"] == \
        " WARC File Format 0.17\r\n"
    assert warc_fixer.source.warcinfo["ip"] == " 0.0.0.0\r\n"
    assert warc_fixer.source.warcinfo["hostname"] == " localhost\r\n"
    assert warc_fixer.source.warcinfo["isPartOf"] == " test collection\r\n"
    assert warc_fixer.source.warcinfo["date"] == \
        " 2021-06-15T18:15:00+00:00\r\n"
    assert warc_fixer.source.warcinfo["software"] == " Test Crawler\r\n"
    assert len(warc_fixer.source.warcinfo) == 9


def test_extract_arc_metadata():
    """
    Test ARC metadata extracting to warcinfo from a warc file directlt created by
    Warctools.
    """
    header = StatusAndHeaders("200 OK", [])
    warc_fixer = WarcFixer({}, "test.warc.gz")
    with open("tests/data/valid_1.0_warctools_resulted.warc") as arc_file:
        count = 0
        for record in ArchiveIterator(arc_file):
            count += 1
            if count == 2:
                break
    warc_fixer.source.set_metadata_record(record)
    warc_fixer._extract_arc_metadata()
    assert warc_fixer.source.warcinfo["conformsTo"] == \
        "http://www.archive.org/web/researcher/ArcFileFormat.php"
    assert warc_fixer.source.warcinfo["description"] == "Test description"
    assert warc_fixer.source.warcinfo["format"] == "ARC file version 1.1"
    assert warc_fixer.source.warcinfo["ip"] == "0.0.0.0"
    assert warc_fixer.source.warcinfo["hostname"] == "localhost"
    assert warc_fixer.source.warcinfo["isPartOf"] == "test collection"
    assert warc_fixer.source.warcinfo["date"] == "2021-06-15T18:15:00+00:00"
    assert warc_fixer.source.warcinfo["software"] == "Test Crawler"
    assert len(warc_fixer.source.warcinfo) == 8
