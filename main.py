#!/usr/bin/env python3
"""One Line, One Laugh — u-coral-404-one-line-one-laugh-22f2c9f3.

Pure Python 3.13 standard library. The program writes one funny line
to /output/entry.txt. No network, no model call, fully deterministic:
the same code always writes the same bytes.

The line (102 characters, plus a trailing newline):

    I told my plants I'm going on holiday. They've already started
    dying out of respect for the tradition.

Why this line (candidates compared against the judge brief, most
important criterion first — funniness, surprise, economy, freshness,
clean wording):

1. CHOSEN: "I told my plants I'm going on holiday. They've already
   started dying out of respect for the tradition." (102 chars) —
   the turn is the whole joke and it lands in the last four words:
   plants dying on holiday is expected; dying "out of respect for
   the tradition" reframes it as deliberate, loyal sabotage. One
   idea, one turn, no filler; the setup is a single short sentence
   and the punchline needs no explanation. Fresh angle — no stock
   joke, no pun, no familiar saying restated.
2. "I bought a treadmill to hang clothes on. It works perfectly —
   the clothes have never been fitter." (99 chars) — the "fitter"
   wordplay is the joke, but the treadmill-as-clothes-rack setup is
   a familiar observation, and a pun is a weaker turn than the
   chosen line's reframing (criteria 2 and 4).
3. "My smartwatch congratulated me on burning 400 calories. I was
   just stress-eating in front of the fridge, standing still."
   (119 chars) — relatable, but two ideas (watch praise + fridge
   confession) and the turn is a deflation, not a surprise
   (criteria 2 and 3).
4. "I asked my smart speaker for the meaning of life. It played an
   ad for life insurance and went silent, like it knew something."
   (122 chars) — a decent turn, but "smart speaker gives a dark
   answer" is a well-worn format and the line is longer than the
   punchline needs (criteria 3 and 4).
5. "My Roomba filed a complaint: it found my sock under the bed and
   has requested hazard pay." (89 chars) — cute, but the turn
   ("hazard pay") is telegraphed by "filed a complaint" and the
   line leaves most of the 200 characters unused (criteria 2
   and 5).

Newline decision: the file ends with exactly one trailing newline.
The gate allows 1 to 200 characters; this file is 103 bytes total
including the newline, so it passes even if the scorer counts the
newline, and the line itself is a single line with no embedded
newline.

Revision notes (reviser pass — what changed vs the builder version,
and the real defect each change closes):

1. Short writes are no longer silently accepted. The builder called
   ``f.write(data)`` once and ignored its return value, so a partial
   write would have produced a truncated entry.txt and the failure
   would only have surfaced later, if at all. ``_write_all`` loops
   until every byte is written and raises on a zero-byte write.
2. Verification now happens BEFORE the publish, not after it. The
   builder read ``entry.txt`` back only after ``os.replace``, so a
   bad write would already have been the published entry by the
   time the mismatch was raised. The tmp file is now fully verified
   (regular file, exact size, mode 0644, exact bytes) before the
   replace, and verified again after it.
3. The tmp file is unique per process. The builder used the fixed
   name ``.entry.txt.tmp``, so two runs sharing an output directory
   would overwrite each other's tmp file mid-write. The tmp name
   now carries the pid (``.entry.txt.<pid>.tmp``), and the stale-tmp
   sweep only removes tmp files whose owner pid is dead — a live
   run's tmp is never touched.
4. ``MAKEFUN_OUTPUT_DIR`` is resolved defensively. The builder
   passed the raw env value to ``makedirs``: an empty string raised
   a cryptic ``FileNotFoundError`` from ``makedirs("")``, and a
   value pointing at an existing regular file raised a bare
   ``FileExistsError``. ``resolve_output_dir`` strips whitespace,
   falls back to ``/output`` on an empty value, and raises a clear
   ``ValueError`` when the path exists and is not a directory.
5. The validator now rejects control characters and stray
   whitespace. The builder only rejected ``\\n`` and ``\\r``; a
   control character such as ``\\x00`` or ``\\x07`` would have
   passed validation even though the gate requires plain UTF-8
   text, and leading/trailing whitespace would have silently
   counted against the 200-character gate. ``validate_line`` now
   rejects every Unicode control character (category Cc, which
   covers C0, DEL and C1), the line/paragraph separators U+2028
   and U+2029, and any leading or trailing whitespace.
6. Post-publish verification is explicit. After the replace, the
   published file is checked again for regular-file type, exact
   size, exact bytes and mode 0644, and the run confirms its own
   tmp file is gone, so no stray tmp can be mistaken for output.
7. Cleanup is guaranteed. The tmp file is removed in a ``finally``
   block, so a failure anywhere in the write path can never leave
   a half-written tmp behind for the next run to trip over.

Usage: mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
"""

import os
import re
import stat
import unicodedata

LINE = (
    "I told my plants I'm going on holiday. They've already started "
    "dying out of respect for the tradition."
)

# Sealed gate: /output/entry.txt must be UTF-8 text of 1 to 200
# characters, not only white space, on a single line.
MAX_LINE_CHARS = 200

OUTPUT_FILENAME = "entry.txt"

# Tmp files are named .entry.txt.<pid>.tmp so concurrent runs never
# share one; the sweep below recognises exactly this shape.
_TMP_RE = re.compile(r"^\.entry\.txt\.(\d+)\.tmp$")


def validate_line(line):
    """Check the line against the gate; raise ValueError if it fails.

    The check runs before any file is written, so an invalid line
    fails loudly instead of producing an entry the scorer rejects.
    It is deliberately stricter than the gate in two places where
    the gate's wording leaves a trap: control characters are not
    "text" a scorer can read cleanly, and leading/trailing
    whitespace only burns characters from the 200-character budget.
    """
    if not isinstance(line, str):
        raise ValueError("line must be a string")
    if not line.strip():
        raise ValueError("line must not be blank or only whitespace")
    if line != line.strip():
        raise ValueError("line must not start or end with whitespace")
    if "\n" in line or "\r" in line:
        raise ValueError("line must be a single line (no embedded newline)")
    if "\u2028" in line or "\u2029" in line:
        raise ValueError("line must not contain a line/paragraph separator")
    for ch in line:
        # Category Cc covers C0 controls, DEL and C1 controls.
        if unicodedata.category(ch) == "Cc":
            raise ValueError(
                "line must not contain control character U+%04X" % ord(ch)
            )
    if len(line) > MAX_LINE_CHARS:
        raise ValueError(
            "line is %d characters, over the %d-character gate"
            % (len(line), MAX_LINE_CHARS)
        )
    return line


def resolve_output_dir():
    """Resolve MAKEFUN_OUTPUT_DIR defensively.

    An unset or blank value falls back to /output. A value that
    points at an existing non-directory (a regular file, a dangling
    symlink, a device) fails here with a clear message instead of
    surfacing later as a confusing makedirs/open error.
    """
    raw = os.environ.get("MAKEFUN_OUTPUT_DIR", "")
    out_dir = raw.strip() or "/output"
    if os.path.lexists(out_dir) and not os.path.isdir(out_dir):
        raise ValueError(
            "MAKEFUN_OUTPUT_DIR %r exists and is not a directory" % out_dir
        )
    return out_dir


def _pid_alive(pid):
    """True if pid names a process that is still running."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # A process exists but belongs to someone else: treat it
        # as alive so its tmp file is never swept away.
        return True
    except OSError:
        return True
    return True


def _sweep_stale_temps(out_dir):
    """Remove tmp files left by earlier crashed runs, if any.

    Only files matching the pid-stamped tmp pattern are considered,
    and only when their owner pid is dead (or unparsable — a name
    that matches the pattern but carries no live pid cannot belong
    to a running process). A live run's tmp is never touched, and
    any failure to clean is best effort: a stale tmp must never
    block a fresh run.
    """
    try:
        names = os.listdir(out_dir)
    except OSError:
        return
    own_pid = os.getpid()
    for name in names:
        match = _TMP_RE.match(name)
        if not match:
            continue
        pid = int(match.group(1))
        if pid == own_pid or _pid_alive(pid):
            continue
        try:
            os.unlink(os.path.join(out_dir, name))
        except OSError:
            pass


def _write_all(f, data):
    """Write every byte of data; a short write is a hard failure.

    A single ``file.write`` call is not guaranteed to consume the
    whole buffer, so loop until the view is empty and raise if a
    call ever writes zero bytes.
    """
    view = memoryview(data)
    while view:
        written = f.write(view)
        if written is None:
            # A raw writer in non-blocking mode; not expected for
            # a regular file, but never spin silently on it.
            raise OSError("write returned None without writing data")
        if written == 0:
            raise OSError("short write: wrote 0 of %d bytes" % len(view))
        view = view[written:]


def _fsync_dir(path):
    """Flush a directory entry to disk; best effort on filesystems
    that do not support it."""
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _verify_file(path, data):
    """Check a file is exactly the bytes we meant to write.

    Regular file, exact size, exact bytes, mode 0644. Used on the
    tmp file BEFORE the publish (so a bad write never becomes the
    entry) and again on the published file afterwards.
    """
    st = os.stat(path)
    if not stat.S_ISREG(st.st_mode):
        raise ValueError("%s is not a regular file" % path)
    if st.st_size != len(data):
        raise ValueError(
            "%s is %d bytes, expected %d" % (path, st.st_size, len(data))
        )
    if stat.S_IMODE(st.st_mode) != 0o644:
        raise ValueError(
            "%s has mode %o, expected 0644" % (path, stat.S_IMODE(st.st_mode))
        )
    with open(path, "rb") as f:
        written = f.read()
    if written != data:
        raise ValueError("read-back mismatch: %s is not the line" % path)


def main():
    validate_line(LINE)
    out_dir = resolve_output_dir()
    # Never delete the output directory itself: the grader mounts it.
    os.makedirs(out_dir, exist_ok=True)
    _sweep_stale_temps(out_dir)
    data = (LINE + "\n").encode("utf-8")
    tmp = os.path.join(out_dir, ".entry.txt.%d.tmp" % os.getpid())
    final = os.path.join(out_dir, OUTPUT_FILENAME)
    try:
        with open(tmp, "wb") as f:
            _write_all(f, data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o644)
        # Verify BEFORE the publish: a bad write must never reach
        # the published path.
        _verify_file(tmp, data)
        os.replace(tmp, final)
        os.chmod(final, 0o644)
        _fsync_dir(out_dir)
    finally:
        # Never leave our tmp behind, even on failure.
        try:
            os.unlink(tmp)
        except OSError:
            pass
    # Post-publish verification: the file the grader will read must
    # be exactly the bytes, at exactly mode 0644, with no tmp left.
    _verify_file(final, data)
    if os.path.lexists(tmp):
        raise ValueError("tmp file %s still exists after publish" % tmp)


if __name__ == "__main__":
    main()
