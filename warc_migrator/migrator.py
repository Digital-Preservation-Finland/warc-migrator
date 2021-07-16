"""
Migrate ARC 1.0/1.1 and WARC 0.17/0.18 to WARC 1.0 and validate it.
"""
import os
import subprocess
import tempfile
import click
from warcio.exceptions import ArchiveLoadFailed
from xml_helpers.utils import decode_utf8
from warc_migrator.warc_fixer import WarcFixer, recompress_warc
from warc_migrator.warctools_handler import convert, is_arc


@click.command()
@click.argument("source_path", metavar="SOURCE",
                type=click.Path(exists=True))
@click.argument("target_path", metavar="TARGET",
                type=click.Path(exists=False))
@click.option("--meta", nargs=2, type=str, multiple=True,
              metavar="<NAME> <VALUE>", default=(),
              help="Warcinfo field name and value to be added to the WARC "
                   "file. Overwrites existing field.")
def warc_migrator_cli(source_path, target_path, meta):
    """
    WARC Migrator.

    Convert ARC 1.0/1.1 or WARC 0.17/0.18 file to WARC 1.0 and adds given
    metadata fields to warcinfo. The given fields overwrite the possibly
    existing fields of the same keys. The resulted file will be a gzipped
    WARC file. This tool also validates the resulted file.

    \b
    SOURCE: Source arc or warc file
    TARGET: Target file (warc.gz)
    """
    # \b above is for help formatting of click library
    count = migrator(source_path, target_path, meta)
    click.echo("Wrote the migrated warc into {} with {} records.".format(
        target_path, count))


def migrator(source_path, target_path, meta):
    """
    Migrate archive file to WARC 1.0.

    :source_path: Source archive file name
    :target_path: Target WARC file name, will be compressed WARC
    :meta: User given metadata fields to warcinfo record
    :returns: Number of records written
    """
    if os.path.exists(target_path):
        raise OSError("Target file already exists.")
    if os.stat(source_path).st_size == 0:
        raise IOError("Empty source file.")

    given_warcinfo = {}
    for field in meta:
        given_warcinfo[decode_utf8(field[0])] = decode_utf8(field[1])

    warc_migr = WarcMigrator(source_path, target_path, given_warcinfo)
    if is_arc(source_path):
        count = warc_migr.migrate_arc()
    else:
        count = warc_migr.migrate_warc()

    run_validation("warctools", target_path)
    run_validation("warcio", target_path)

    return count


def run_validation(tool, filename, stdout=subprocess.PIPE):
    """
    Validate the WARC file.

    :tool: Tool used for validation
    :filename: WARC file
    :stdout: Output stream for stdout
    :returns: Tuple of (returncode, stdout, stderr)
    :raises: ValidationException if return code is not 0
    """
    if tool == "warctools":
        command = ["warcvalid", filename]
    elif tool == "warcio":
        command = ["warcio", "check", filename]
    else:
        raise ValidationError("Undefined tool %s." % tool)
    proc = subprocess.Popen(command, stdout=stdout, stderr=subprocess.PIPE,
                            shell=False, env=os.environ.copy())
    (stdout, stderr) = proc.communicate()
    returncode = proc.returncode
    if stdout is None:
        stdout = ""
    if stderr is None:
        stderr = ""

    if returncode != 0:
        error = "\n".join(
            ["Failed: returncode %s" % returncode, decode_utf8(stdout),
             decode_utf8(stderr)])
        raise ValidationError(error)
    return (returncode, stdout, stderr)


class ValidationError(Exception):
    """Exception class for ValidationError"""
    pass


class WarcMigrator(object):
    """
    WARC migrator class.
    """

    def __init__(self, source_path, target_path, given_warcinfo):
        """
        Initalize.

        :source_path: Source path
        :target_path: Target path
        :given_warcinfo: Given warcinfo fields
        """
        self.source_path = source_path
        self.target_path = target_path
        self.given_warcinfo = given_warcinfo

    def _fix_warc_file(self, source, orig_arc_file):
        """
        Fix WARC file.

        If WARC file is gzipped with a single gzip comprssion, it will be
        recompresed so that each record in the file are compressed separately.

        :source: WARC source file handler
        :orig_arc_file: True for WARC migrated from ARC, False otherwise
        """
        warc_fixer = WarcFixer(self.given_warcinfo,
                               target_name=os.path.basename(self.target_path))
        if orig_arc_file:
            fix_warc = warc_fixer.fix_warc_migrated
        else:
            fix_warc = warc_fixer.fix_warc_original

        try:
            with open(self.target_path, "wb") as target:
                count = fix_warc(source, target)
        except ArchiveLoadFailed as err:
            if "ERROR: non-chunked gzip file detected" in str(err):
                with tempfile.NamedTemporaryFile(prefix="warc-migrator.") as \
                        tmp_warc:
                    recompress_warc(source, tmp_warc)
                    with open(self.target_path, "wb") as target:
                        count = fix_warc(tmp_warc, target)
            else:
                raise

        return count

    def migrate_warc(self):
        """
        Migrate WARC 0.17/0.18 file to WARC 1.0
        """
        with open(self.source_path, "rb") as source_buffer:
            return self._fix_warc_file(source_buffer, False)

    def migrate_arc(self):
        """
        Migrate ARC 1.0/1.1 file to WARC 1.0
        """
        with tempfile.NamedTemporaryFile(prefix="warc-migrator.") as \
                source_buffer:
            count = convert(self.source_path, source_buffer)
            source_buffer.seek(0)
            source = source_buffer

            recount = self._fix_warc_file(source_buffer, True)

        if recount != count:
            raise ValueError("Count mismatch, originally %s records, recounted "
                             "%s records." % (count, recount))

        return recount


if __name__ == '__main__':
    warc_migrator_cli()  # pylint: disable=no-value-for-parameter
