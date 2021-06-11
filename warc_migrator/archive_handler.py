"""
Handler for warcinfo and metadata records.
"""
from io import BytesIO
import six
from warcio.recordbuilder import RecordBuilder
from xml_helpers.utils import decode_utf8, encode_utf8


class ArchiveHandler(object):
    """
    Handler for warcinfo and metadata record read from a file or
    to be written to a file.
    """

    def __init__(self):
        """
        Initalize handler.
        """
        self.metadata = b""          # Metadata record payload
        self.warcinfo = {}           # Warcinfo dict
        self.metadata_record = None  # Warcio metadata record
        self.warcinfo_record = None  # Warcio warcinfo record

    def add_warcinfo(self, warcinfo):
        """
        Add a warcinfo dict.

        :warcinfo: Warcinfo dict to be added
        """
        self.warcinfo = warcinfo

    def add_warcinfo_field(self, key, value):
        """
        Add or replace an element to warcinfo dict.

        :key: Key to be added
        :value: Value to be added
        """
        self.warcinfo[decode_utf8(key)] = decode_utf8(value)

    def append_metadata(self, metadata):
        """
        Append a block to metadata payload.

        :metadata: Metadata string.
        """
        self.metadata += encode_utf8(metadata)

    def add_metadata_record(self, record):
        """
        Add Warcio record of metadata.

        :record: Metadata record
        """
        self.metadata_record = record

    def add_warcinfo_record(self, record):
        """
        Add Warcio record of warcinfo.

        :record: Warcinfo record
        """
        self.warcinfo_record = record

    def create_metadata_record(self, header):
        """
        Create new record from given header, payload and record type.

        :header: WARC header
        """
        builder = RecordBuilder("WARC/1.0")
        byte_payload = BytesIO(encode_utf8(self.metadata))
        self.add_metadata_record(builder.create_warc_record(
            uri=None, record_type="metadata", payload=byte_payload,
            warc_headers=header))

    def create_warcinfo_record(self, header):
        """
        Create new record from given header, payload and record type.

        :header: WARC header
        """
        builder = RecordBuilder("WARC/1.0")
        byte_payload = BytesIO(encode_utf8(self._make_warcinfo_payload()))
        self.add_warcinfo_record(builder.create_warc_record(
            uri=None, record_type="metadata", payload=byte_payload,
            warc_headers=header))

    def _make_warcinfo_payload(self):
        """
        Create payload from warcinfo dict for warcinfo record.

        :returns: Warcinfo as payload
        """
        payload = b""
        if six.PY2:
            iterator = self.warcinfo.iteritems()
        else:
            iterator = self.warcinfo.items()
        for (key, value) in iterator:
            if not value.startswith(" "):
                value = " " + value
            if not value.endswith("\r\n"):
                value = value + "\r\n"
            payload = payload + b"%s:%s" % (encode_utf8(key), encode_utf8(value))
        return payload
