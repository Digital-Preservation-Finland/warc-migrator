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
    migrate_to_warc(source_path, target_path, meta)
    click.echo("Wrote the migrated warc into {}".format(target_path))


def migrate_to_warc(source_path, target_path, meta):
    """
    Migrate archive file to WARC 1.0.

    :source_path: Source archive file name
    :target_path: Target WARC file name, will be compressed WARC
    :meta: User given metadata fields to warcinfo record
    """
    if os.path.exists(target_path):
        raise OSError("Target file already exists.")
    if os.stat(source_path).st_size == 0:
        raise IOError("Empty source file.")

    given_warcinfo = {}
    for field in meta:
        given_warcinfo[decode_utf8(field[0])] = decode_utf8(field[1])

    arc_file = is_arc(source_path)
    warc_fixer = WarcFixer(given_warcinfo,
                           target_name=os.path.basename(target_path))

    with tempfile.NamedTemporaryFile(prefix="warc-migrator.") if arc_file \
            else open(source_path, "rb") as source_buffer:
        if arc_file:
            count = convert(source_path, source_buffer)
            source_buffer.seek(0)
            source = source_buffer
        else:
            source = source_buffer

        try:
            with open(target_path, "wb") as target:
                recount = warc_fixer.fix_warc(source, target, arc_file)
        except ArchiveLoadFailed as err:
            if "ERROR: non-chunked gzip file detected" in str(err):
                with tempfile.NamedTemporaryFile(prefix="warc-migrator.") as \
                        tmp_warc:
                    recompress_warc(source, tmp_warc)
                    with open(target_path, "wb") as target:
                        recount = warc_fixer.fix_warc(tmp_warc, target, arc_file)
            else:
                raise

    if arc_file and recount != count:
        raise ValueError("Count mismatch, originally %s records, recounted "
                         "%s records." % (count, recount))

    run_validation("warctools", target_path)
    run_validation("warcio", target_path)


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


if __name__ == '__main__':
    warc_migrator_cli()  # pylint: disable=no-value-for-parameter
