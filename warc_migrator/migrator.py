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
@click.argument("source_path", metavar="SOURCE", type=click.Path(exists=True))
@click.argument("target_path", metavar="TARGET", type=click.Path(exists=False))
@click.option("--meta", nargs=2, type=str, multiple=True,
              metavar="<NAME> <VALUE>", default=(),
              help="Warcinfo field name and value to be added to the WARC file."
                   "Overwrites existing field.")
def warc_migrator_cli(source_path, target_path, meta):
    """
    WARC Migrator.

    Convert ARC 1.0/1.1 or WARC 0.17/0.18 file to WARC 1.0 and adds given
    metadata fields to warcinfo, but only, if the given fields are originally
    missing. The resulted file will be a gzipped WARC file. This tool also
    validates the resulted file.

    \b
    SOURCE: Source arc or warc file
    TARGET: Target file (warc.gz)
    """
    # \b above is for help formatting of click library
    warc_migrator(source_path, target_path, meta)


def warc_migrator(source_path, target_path, meta):
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
            else open(source_path, 'rb') as source_buffer:
        if arc_file:
            count = convert(source_path, source_buffer)
            source_buffer.seek(0)
            source = source_buffer
        else:
            source = source_buffer

        try:
            with open(target_path, 'wb') as target:
                recount = warc_fixer.fix_warc(source, target, arc_file)
        except ArchiveLoadFailed as err:
            message = "non-chunked gzip file detected, gzip block " \
                      "continues beyond single record"
            if message in err:
                source.seek(0)
                with tempfile.NamedTemporaryFile(prefix="warc-migrator.") as \
                        tmp_warc:
                    recompress_warc(source, tmp_warc)
                    tmp_warc.seek(0)
                    with open(target_path, 'wb') as target:
                        recount = warc_fixer.fix_warc(tmp_warc, target, arc_file)
            else:
                raise ArchiveLoadFailed(err)

    if arc_file and recount != count:
        raise ValueError("Count mismatch, originally %s records, recounted "
                         "%s records." % (count, recount))

    validate(target_path)


def validate(warc_file):
    """
    Validate given WARC file.

    :warc_file: WARC filename
    """
    _shell(["warcvalid", warc_file])
    _shell(["warcio", "check", warc_file])


def _shell(command, stdout=subprocess.PIPE):
    """
    Run the given command in shell.

    :command: Given command
    :stdout: Output stream for stdout
    :returns: Tuple of (returncode, stdout, stderr)
    :raises: ValueError if return code of command run in shell is not 0
    """
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
        raise ValueError(error)
    return (returncode, stdout, stderr)


if __name__ == '__main__':
    warc_migrator_cli()
