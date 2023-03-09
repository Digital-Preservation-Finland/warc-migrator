"""
Fix produced WARC file to WARC 1.0.
"""
import os
import datetime
from copy import deepcopy
import six
import lxml.etree as ET
from warcio.warcwriter import WARCWriter
from warcio.archiveiterator import ArchiveIterator
from warcio.bufferedreaders import DecompressingBufferedReader
from warc_migrator.archive_handler import ArchiveHandler


# Pylint doesn't know what members lxml.etree has or doesn't have
# pylint: disable=c-extension-no-member


def recompress_warc(source, target):
    """
    Recompress a WARC file. This is used for fixing a compression
    issue. Originally, some implementations created WARC compression in a
    wrong way, and this is used to resolve it.

    :source: Source file buffer
    :target: Target file buffer
    """
    source.seek(0)
    decomp_buff = DecompressingBufferedReader(
        source, read_all_members=True)
    writer = WARCWriter(filebuf=target, gzip=True)
    for record in ArchiveIterator(
            decomp_buff, no_record_parse=False,
            arc2warc=False, verify_http=False):
        writer.write_record(record)
    target.seek(0)


# pylint: disable=too-few-public-methods
class WarcFixer(object):
    """
    Fix WARC file in various ways.

    If WARC file is resulted from an ARC file: Assume that warcinfo is the
    first record and metadata record about old ARC is the second record.
    This is the normal output of Warctools' arc2warc script. These records are
    fixed.

    If WARC file is resulted from a WARC file: Find the first warcinfo record
    and fix it.

    All other records are unchanged.
    """

    def __init__(self, given_warcinfo, target_name):
        """
        Initialize engine.

        :given_warcinfo: Dict of warcinfo fields given by the user
        :target_name: Target WARC filename
        """

        self.source = ArchiveHandler()
        self.target = ArchiveHandler()
        self.given_warcinfo = given_warcinfo
        self.target_name = target_name

    def fix_warc_migrated(self, source_handler, target_handler):
        """
        Fix WARC file migrated from ARC 1.0/1.1 file.
        - Convert possible ARC XML metadata to warcinfo
        - Fix mimetype in ARC metadata record
        - Change protocol in all records to WARC/1.0
        - If necessary, URL encode HTTP header in the record
        - Compute block and payload digests
        - Update filename and timestamp in WARC header
        - Update warcinfo with user-defined fields and to meet WARC 1.0 spec

        :source_handler: Source file handler
        :target_handler: Target file handler
        :return: Count of written records
        """
        count = 0
        warcinfo_fixed = False
        warc_writer = WARCWriter(target_handler, warc_version="1.0",
                                 gzip=True)
        for record in ArchiveIterator(fileobj=source_handler,
                                      no_record_parse=False,
                                      verify_http=False, arc2warc=False,
                                      ensure_http_headers=False):
            if not warcinfo_fixed:
                if record.rec_type == "warcinfo" and \
                        record.content_type == "application/warc-fields":
                    self.source.set_warcinfo_record(record)
                elif record.rec_type == "metadata" and \
                        record.content_type == "application/arc":
                    self.source.set_metadata_record(record)
                    self._extract_arc_metadata()
                    self._fix_metadata()
                    self._fix_warcinfo()
                    warc_writer.write_record(self.target.warcinfo_record)
                    warc_writer.write_record(self.target.metadata_record)
                    count += 2
                    warcinfo_fixed = True
            else:
                self._fix_warc_data_record(record)
                warc_writer.write_record(record)
                count += 1

        return count

    def fix_warc_original(self, source_handler, target_handler):
        """
        Fix WARC 0.17/0.18 file.
        - Change protocol in all records to WARC/1.0
        - If necessary, URL encode HTTP header in the record
        - Compute block and payload digests
        - Update filename and timestamp in WARC header
        - Update warcinfo with user-defined fields and to meet WARC 1.0 spec

        :source_handler: Source file handler
        :target_handler: Target file handler
        :return: Count of written records
        """
        count = 0
        warcinfo_fixed = False
        warc_writer = WARCWriter(target_handler, warc_version="1.0",
                                 gzip=True)
        for record in ArchiveIterator(fileobj=source_handler,
                                      no_record_parse=False,
                                      verify_http=False, arc2warc=False,
                                      ensure_http_headers=False):
            if record.rec_type == "warcinfo" and \
                    record.content_type == "application/warc-fields" and \
                    not warcinfo_fixed:
                self.source.set_warcinfo_record(record)
                self._extract_warcinfo()
                self._fix_warcinfo()
                warc_writer.write_record(self.target.warcinfo_record)
                count += 1
                warcinfo_fixed = True
            else:
                self._fix_warc_data_record(record)
                warc_writer.write_record(record)
                count += 1

        return count

    def _fix_warc_data_record(self, record):
        """
        Fix WARC data record, other than warcinfo of ARC mewtadata record.
        - Change protocol to WARC/1.0
        - If necessary, URL encode HTTP header in the record

        :record: WARC data record
        """
        # pylint: disable=no-self-use
        record.rec_headers.protocol = "WARC/1.0"
        if record.http_headers:
            status = record.http_headers.statusline.split(" ", 1)
            if len(status) > 1:
                try:
                    status[1].encode('ascii')
                except (UnicodeEncodeError, UnicodeDecodeError):
                    record.http_headers.statusline = " ".join(
                        [status[0], six.moves.urllib.parse.quote(status[1])])

    def _fix_warcinfo(self):
        """
        Fixes WARC's warcinfo record in various ways:
        - Rewrite conformsTo and format fields in warcinfo.
        - Add user given fields. Overwrites, if exists.
        - Rewrite WARC-Date and WARC-Filename fields from the header.
        """
        self.target.set_warcinfo(deepcopy(self.source.warcinfo))
        self.target.warcinfo["conformsTo"] = \
            ["https://iipc.github.io/warc-specifications/"
             "specifications/warc-format/warc-1.0/"]
        self.target.warcinfo["format"] = ["WARC File Format 1.0"]
        for key, values in self.given_warcinfo.items():
            for value in values:
                self.target.set_warcinfo_field(key, value)
        self.target.create_info_record(
            self.source.warcinfo_record.rec_headers, "warcinfo")

        record_headers = self.target.warcinfo_record.rec_headers

        # We want to replace (or add, if missing) a few fields to WARC header.
        # The header field is a (key, value) tuple and we do not know the
        # actual values (filename and timestamp). Therefore, we first list
        # them to remove those and then append.
        for field in list(record_headers.headers):
            if "WARC-Filename" in field or "WARC-Date" in field:
                record_headers.headers.remove(field)
        record_headers.headers.append((
            "WARC-Filename", os.path.basename(self.target_name)))
        date = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        record_headers.headers.append(("WARC-Date", date))
        record_headers.protocol = "WARC/1.0"

    def _fix_metadata(self):
        """
        Change content type of metadata record containing old ARC file header
        to application/x-internet-archive
        """
        self.target.metadata = self.source.metadata
        self.target.create_info_record(
            self.source.metadata_record.rec_headers, "metadata")
        self.target.metadata_record.content_type = \
            "application/x-internet-archive"
        self.target.metadata_record.rec_headers.protocol = "WARC/1.0"

    def _extract_warcinfo(self):
        """
        Extract metadata from warcinfo record to dict.
        """
        while self.source.warcinfo_record.raw_stream.limit > 0:
            field = self.source.warcinfo_record.raw_stream.readline()
            if field == b"\r\n":
                break
            split_row = field.split(b":", 1)
            self.source.set_warcinfo_field(split_row[0], split_row[1])

    def _extract_arc_metadata(self):
        """
        Create warcinfo from ARC metadata in WARC metadata record.
        Supports ARC and Dublin Core (DC 1.1, DC Terms, DCMIType) metadat
        fields.
        """
        line = b""
        metadata = b""
        while not line.startswith(b"<") and \
                self.source.metadata_record.raw_stream.limit > 0:
            line = self.source.metadata_record.raw_stream.readline()
            self.source.append_metadata(line)
        if not line.startswith(b"<"):
            return

        metadata = line
        while self.source.metadata_record.raw_stream.limit != 0:
            meta = self.source.metadata_record.raw_stream.read()
            self.source.append_metadata(meta)
            metadata = metadata + meta
        xml = ET.fromstring(metadata)
        nspace = {"arc": "http://archive.org/arc/1.0/",
                  "dc": "http://purl.org/dc/elements/1.1/",
                  "dcterms": "http://purl.org/dc/terms/",
                  "dcmitype": "http://purl.org/dc/dcmitype/"}
        arc_metadata = xml.xpath(
            "//arc:* | //dc:* | //dcterms:* | //dcmitype:*",
            namespaces=nspace)
        for field in arc_metadata:
            tagname = field.tag.split("}")[1]
            if tagname != "arcmetadata":
                self.source.set_warcinfo_field(tagname, field.text)
