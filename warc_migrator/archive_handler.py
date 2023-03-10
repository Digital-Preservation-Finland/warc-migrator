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

    def set_warcinfo(self, warcinfo):
        """
        Set a warcinfo dict.

        :warcinfo: Warcinfo dict to be added
        """
        self.warcinfo = warcinfo

    def add_warcinfo_field(self, key, value):
        """
        The values of the warcinfo dict are lists so multiple values of
        warcinfo fields with the same name can be stored.
        This adds a new value to a key if it already exists in the dict, or
        creates a new element in the dict if not.

        :key: Key to be added
        :value: Value to be added
        """
        if self.warcinfo.get(decode_utf8(key)):
            self.warcinfo[decode_utf8(key)].append(decode_utf8(value))
        else:
            self.warcinfo[decode_utf8(key)] = [decode_utf8(value)]

    def append_metadata(self, metadata):
        """
        Append a block to metadata payload.

        :metadata: Metadata string.
        """
        self.metadata += encode_utf8(metadata)

    def set_metadata_record(self, record):
        """
        Set Warcio record of metadata.

        :record: Metadata record
        """
        self.metadata_record = record

    def set_warcinfo_record(self, record):
        """
        Set Warcio record of warcinfo.

        :record: Warcinfo record
        """
        self.warcinfo_record = record

    def create_info_record(self, header, record_type):
        """
        Create new info record from given header and record type.

        :header: WARC header
        :record_type: Record type: "warcinfo" or "metadata"
        """
        builder = RecordBuilder("WARC/1.0")
        if record_type == "metadata":
            self.set_metadata_record(builder.create_warc_record(
                uri=None,
                record_type=record_type,
                payload=BytesIO(encode_utf8(self.metadata)),
                warc_headers=header
            ))
        elif record_type == "warcinfo":
            self.set_warcinfo_record(builder.create_warc_record(
                uri=None,
                record_type=record_type,
                payload=BytesIO(encode_utf8(self._make_warcinfo_payload())),
                warc_headers=header
            ))

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
        for key, values in iterator:
            for value in values:
                if not value.startswith(" "):
                    value = " " + value
                if not value.endswith("\r\n"):
                    value = value + "\r\n"
                payload = payload + b"%s:%s" % (encode_utf8(key),
                                                encode_utf8(value))
        return payload
