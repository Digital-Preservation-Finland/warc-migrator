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
from warc_migrator.archive_handler import ArchiveHandler


def recompress_warc(source, target):
    """
    Open a WARC file an rewrite it to fix compression problems.
    Originally some implementations created warc compression in a wrong but
    readable way. Recompressing the warc fixes this.
    """
    writer = WARCWriter(filebuf=target, gzip=True)
    for record in ArchiveIterator(
            source, no_record_parse=False,
            arc2warc=False, verify_http=False):
        if record.http_headers:
            record.http_headers = SimpleHeader(record.http_headers)
        writer.write_record(record)


class SimpleHeader(object):
    """
    Fake buffer of Warcio HTTP header to avoid encoding of bytes.
    """
    def __init__(self, headers):
        """
        Warcio has headers_buff attribute for header infomation.
        TODO: Assumes ISO-8859-1 encoding in Python3. Could be something else.

        :headers: Warcio record header
        """
        if six.PY2:
            self.headers_buff = headers.to_str() + b"\r\n"
        else:
            self.headers_buff = headers.to_str().encode("iso-8859-1") + b"\r\n"

    def compute_headers_buffer(self, header_filter=None):
        """
        Just skip the computing operations to heaader buffer.
        """
        pass


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

    def fix_warc(self, source_handler, target_handler, arc_file, encode):
        """
        Fix WARC file in various ways, see class comment for details.

        :source_handler: Source file handler
        :target_handler: Target file handler
        :arc_file: True for original ARC file, False for original WARC file
        :encode: True for HTTP header encoding, False for skipping encoding
        """
        count = 0
        warcinfo_fixed = False
        warc_writer = WARCWriter(target_handler, warc_version="1.0",
                                 gzip=True)
        for record in ArchiveIterator(fileobj=source_handler,
                                      no_record_parse=False,
                                      verify_http=False, arc2warc=False,
                                      ensure_http_headers=False):
            if arc_file and not warcinfo_fixed:
                if record.rec_type == "warcinfo" and \
                        record.content_type == "application/warc-fields":
                    self.source.add_warcinfo_record(record)
                    continue
                elif record.rec_type == "metadata" and \
                        record.content_type == "application/arc":
                    self.source.add_metadata_record(record)
                    self._extract_arc_metadata()
                    self._fix_metadata()
                    self._fix_warcinfo()
                    warc_writer.write_record(self.target.warcinfo_record)
                    warc_writer.write_record(self.target.metadata_record)
                    count += 2
                    warcinfo_fixed = True
            elif not arc_file and record.rec_type == "warcinfo" and \
                    record.content_type == "application/warc-fields" and \
                    not warcinfo_fixed:
                self.source.add_warcinfo_record(record)
                self._extract_warcinfo()
                self._fix_warcinfo()
                warc_writer.write_record(self.target.warcinfo_record)
                count += 1
                warcinfo_fixed = True
            else:
                record.rec_headers.protocol = "WARC/1.0"
                if record.http_headers:
                    if encode:
                        status = record.http_headers.statusline.split(" ", 1)
                        if len(status) > 1:
                            try:
                                status[1].encode('ascii')
                            except:
                                record.http_headers.statusline = " ".join(
                                    [status[0],
                                     six.moves.urllib.parse.quote(status[1])])
                    else:
                        record.http_headers = SimpleHeader(
                            record.http_headers)
                warc_writer.write_record(record)
                count += 1

        return count

    def _fix_warcinfo(self):
        """
        Fixes WARC's warcinfo record in various ways:
        - Rewrite comformsTo and format fields in warcinfo.
        - Add user given fields. Overwrites, if exists.
        - Rewrite WARC-Date and WARC-Filename fields from the header.
        """
        self.target.add_warcinfo(deepcopy(self.source.warcinfo))
        self.target.warcinfo["conformsTo"] = \
            "https://iipc.github.io/warc-specifications/" \
            "specifications/warc-format/warc-1.0/"
        self.target.warcinfo["format"] = "WARC File Format 1.0"
        for key, value in self.given_warcinfo.items():
            self.target.warcinfo[key] = value
        self.target.create_warcinfo_record(
            self.source.warcinfo_record.rec_headers)
        remove_field = []
        for field in self.target.warcinfo_record.rec_headers.headers:
            if "WARC-Filename" in field or "WARC-Date" in field:
                remove_field.append(field)
        for field in remove_field:
            self.target.warcinfo_record.rec_headers.headers.remove(field)
        self.target.warcinfo_record.rec_headers.headers.append((
            "WARC-Filename", os.path.basename(self.target_name)))
        date = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        self.target.warcinfo_record.rec_headers.headers.append(("WARC-Date", date))
        self.target.warcinfo_record.rec_headers.protocol = "WARC/1.0"

    def _fix_metadata(self):
        """
        Change content type of metadata record containing old ARC file header
        to application/x-internet-archive
        """
        self.target.metadata = self.source.metadata
        self.target.create_metadata_record(self.source.metadata_record.rec_headers)
        self.target.metadata_record.content_type = "application/x-internet-archive"
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
            self.source.add_warcinfo_field(split_row[0], split_row[1])

    def _extract_arc_metadata(self):
        """
        Create warcinfo from ARC metadata in WARC metadata record.
        Supports ARC and Dublin Core (DC 1.1, DC Terms, DCMIType) metadata fields.
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
        ns = {"arc": "http://archive.org/arc/1.0/",
              "dc": "http://purl.org/dc/elements/1.1/",
              "dcterms": "http://purl.org/dc/terms/",
              "dcmitype": "http://purl.org/dc/dcmitype/"}
        arc_metadata = xml.xpath("//arc:* | //dc:* | //dcterms:* | //dcmitype:*",
                                 namespaces=ns)
        for field in arc_metadata:
            tagname = field.tag.split("}")[1]
            if tagname != "arcmetadata":
                self.source.add_warcinfo_field(tagname, field.text)
