"""
Test the methods of ArchiveHandler
"""
from warc_migrator.archive_handler import ArchiveHandler
from warcio.statusandheaders import StatusAndHeaders


def test_archive_handler():
    """
    Test the attribute setters of ArchiveHandler.
    """
    archive = ArchiveHandler()
    archive.set_warcinfo({"key1": "value1"})
    archive.set_warcinfo_field("key2", "value2")
    archive.append_metadata("append1")
    archive.append_metadata("append2")
    archive.set_metadata_record("fakerecord1")
    archive.set_warcinfo_record("fakerecord2")
    assert archive.warcinfo == {"key1": "value1", "key2": "value2"}
    assert archive.metadata == b"append1append2"
    assert archive.metadata_record == "fakerecord1"
    assert archive.warcinfo_record == "fakerecord2"


def test_create_info_record():
    """
    Test warcinfo and metadata record creation.
    """
    archive = ArchiveHandler()
    headers = StatusAndHeaders(
        "200 OK", [("field1", "value1"), ("field2", "value2")])
    archive.warcinfo = {"info1": "infovalue1", "info2": "infovalue2"}
    archive.metadata = b"Test metadata"
    archive.create_info_record(headers, "warcinfo")
    info1 = archive.warcinfo_record.raw_stream.readline()
    info2 = archive.warcinfo_record.raw_stream.readline()
    assert archive.warcinfo_record.rec_headers == headers
    assert archive.warcinfo_record.rec_type == "warcinfo"
    assert info1 == b"info1: infovalue1\r\n"
    assert info2 == b"info2: infovalue2\r\n"

    archive.create_info_record(headers, "metadata")
    info = archive.metadata_record.raw_stream.readline()
    assert archive.metadata_record.rec_headers == headers
    assert archive.metadata_record.rec_type == "metadata"
    assert info == b"Test metadata"


def test_make_warcinfo_payload():
    """
    Test converting the warcinfo dict to byte payload.
    """
    archive = ArchiveHandler()
    archive.warcinfo = {"info1": "infovalue1", "info2": "infovalue2"}
    payload = archive._make_warcinfo_payload()
    assert payload == b"info1: infovalue1\r\ninfo2: infovalue2\r\n"
