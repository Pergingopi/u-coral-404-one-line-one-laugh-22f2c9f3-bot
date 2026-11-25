#!/usr/bin/env python3
"""One Line, One Laugh — u-coral-404-one-line-one-laugh-22f2c9f3.

Pure Python 3.13 standard library. The program writes one funny line
to /output/entry.txt. No network, no model call, fully deterministic:
the same code always writes the same bytes.

The line (102 characters, plus a trailing newline):

    I told my plants I'm going on holiday. They've already started
    dying out of respect for the tradition.

Why this line — candidates judged against the brief, funniness first,
then surprise, economy, freshness, clean wording:

* CHOSEN (102 chars): plants dying on holiday is expected; dying
  "out of respect for the tradition" reframes it as deliberate,
  loyal sabotage. One idea, one turn, no filler; the punchline
  needs no explanation. Fresh angle — no stock joke, no pun.
* Treadmill (99): "I bought a treadmill to hang clothes on. It works
  perfectly — the clothes have never been fitter." The "fitter"
  wordplay is the joke, but the setup is a familiar observation and
  a pun is a weaker turn than a reframe.
* Smartwatch (119): "My smartwatch congratulated me on burning 400
  calories. I was just stress-eating in front of the fridge,
  standing still." Relatable, but two ideas at once and the turn is
  a deflation, not a surprise.
* Smart speaker (122): "I asked my smart speaker for the meaning of
  life. It played an ad for life insurance and went silent, like it
  knew something." Decent turn, but a well-worn format and longer
  than the punchline needs.
* Roomba (89): "My Roomba filed a complaint: it found my sock under
  the bed and has requested hazard pay." Cute, but "hazard pay" is
  telegraphed by "filed a complaint" and the line leaves most of
  the 200 characters unused.

Newline decision: the file ends with exactly one trailing newline.
The gate allows 1 to 200 characters; this file is 103 bytes total
including the newline, so it passes even if the scorer counts the
newline, and the line itself is a single line with no embedded
newline.

Structure of this file (second revision pass — what changed vs the
first reviser pass, and why):

* The publish sequence is now a class, ``AtomicPublisher``. The
  first reviser pass left ``main()`` doing four jobs at once
  (prepare the directory, write the tmp file, publish it, confirm
  the result); each step is now a named method — ``prepare``,
  ``publish``, ``confirm`` — so a defect in one step can be fixed
  without touching the others.
* Validation is split into one small check per rule instead of a
  single long function. ``check_line`` runs the checks in order and
  fails on the first one; each ``_reject_*`` helper owns exactly
  one rule (blank, edge whitespace, line breaks, separators,
  control characters, length). The rules themselves are unchanged:
  the builder only rejected ``\\n`` and ``\\r``, the first reviser
  added the rest, and this pass keeps every one of them.
* File verification is split the same way: ``_check_stat`` owns
  the regular-file / size / mode 0644 checks and ``_check_bytes``
  owns the byte-for-byte read-back; ``_check_file`` runs both.
  The tmp file is still verified BEFORE ``os.replace`` and the
  published file again afterwards, exactly as before.
* Helpers are renamed to what they do: ``validate_line`` is now
  ``check_line``, ``resolve_output_dir`` is now ``output_dir``,
  ``_write_all`` is now ``_drain``, ``_verify_file`` is now
  ``_check_file``. The tmp sweep now goes through
  ``_tmp_owner_dead``, which owns the pid-parsing decision that
  used to be inline in the sweep loop.
* Behaviour is identical to the first reviser pass: same line,
  same gate, same atomic write (tmp + fsync + verify + replace +
  fsync dir), same per-pid tmp names, same sweep of dead owners
  only, same cleanup in ``finally``.

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


def _tmp_name(pid):
    """Tmp file name for a process; the pid stamp keeps concurrent
    runs in one output directory from sharing a tmp file."""
    return ".entry.txt.%d.tmp" % pid


def _reject_blank(line):
    """The line must contain something other than whitespace."""
    if not line.strip():
        raise ValueError("line must not be blank or only whitespace")


def _reject_edge_whitespace(line):
    """Leading/trailing whitespace only burns gate characters."""
    if line != line.strip():
        raise ValueError("line must not start or end with whitespace")


def _reject_line_breaks(line):
    """The entry is one line; embedded breaks are not allowed."""
    if "\n" in line or "\r" in line:
        raise ValueError("line must be a single line (no embedded newline)")


def _reject_separators(line):
    """U+2028/U+2029 are line breaks in disguise."""
    if "\u2028" in line or "\u2029" in line:
        raise ValueError("line must not contain a line/paragraph separator")


def _reject_controls(line):
    """Control characters are not text a scorer can read cleanly."""
    for ch in line:
        # Category Cc covers C0 controls, DEL and C1 controls.
        if unicodedata.category(ch) == "Cc":
            raise ValueError(
                "line must not contain control character U+%04X" % ord(ch)
            )


def _reject_too_long(line):
    """The gate caps the line at MAX_LINE_CHARS characters."""
    if len(line) > MAX_LINE_CHARS:
        raise ValueError(
            "line is %d characters, over the %d-character gate"
            % (len(line), MAX_LINE_CHARS)
        )


def check_line(line):
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
    for check in (
        _reject_blank,
        _reject_edge_whitespace,
        _reject_line_breaks,
        _reject_separators,
        _reject_controls,
        _reject_too_long,
    ):
        check(line)
    return line


def output_dir():
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


def _process_alive(pid):
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


def _tmp_owner_dead(name):
    """True if a pid-stamped tmp name belongs to no live process.

    A name that matches the pattern but carries no live pid cannot
    belong to a running process, so it is safe to sweep. The caller's
    own pid is never dead to itself.
    """
    match = _TMP_RE.match(name)
    if not match:
        return False
    pid = int(match.group(1))
    return pid != os.getpid() and not _process_alive(pid)


def _clear_dead_temps(out_dir):
    """Remove tmp files left by earlier crashed runs, if any.

    Only files matching the pid-stamped tmp pattern are considered,
    and only when their owner pid is dead. A live run's tmp is never
    touched, and any failure to clean is best effort: a stale tmp
    must never block a fresh run.
    """
    try:
        names = os.listdir(out_dir)
    except OSError:
        return
    for name in names:
        if not _tmp_owner_dead(name):
            continue
        try:
            os.unlink(os.path.join(out_dir, name))
        except OSError:
            pass


def _drain(f, data):
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


def _sync_dir(path):
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


def _check_stat(path, data):
    """Check a file is a regular file of the right size and mode."""
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


def _check_bytes(path, data):
    """Check a file holds exactly the bytes we meant to write."""
    with open(path, "rb") as f:
        written = f.read()
    if written != data:
        raise ValueError("read-back mismatch: %s is not the line" % path)


def _check_file(path, data):
    """Check a file is exactly the bytes we meant to write.

    Regular file, exact size, exact bytes, mode 0644. Used on the
    tmp file BEFORE the publish (so a bad write never becomes the
    entry) and again on the published file afterwards.
    """
    _check_stat(path, data)
    _check_bytes(path, data)


class AtomicPublisher:
    """Owns the tmp → verify → replace → verify publish sequence.

    One instance serves one run: it knows the output directory, the
    per-pid tmp path and the final path, and it guarantees the tmp
    file is cleaned up even when a step fails.
    """

    def __init__(self, out_dir):
        self.out_dir = out_dir
        self.tmp = os.path.join(out_dir, _tmp_name(os.getpid()))
        self.final = os.path.join(out_dir, OUTPUT_FILENAME)

    def prepare(self):
        """Create the output directory and sweep dead tmp files.

        Never delete the output directory itself: the grader mounts
        it, so only its contents are ever touched.
        """
        os.makedirs(self.out_dir, exist_ok=True)
        _clear_dead_temps(self.out_dir)

    def publish(self, data):
        """Write data to tmp, verify it, then atomically replace."""
        try:
            with open(self.tmp, "wb") as f:
                _drain(f, data)
                f.flush()
                os.fsync(f.fileno())
            os.chmod(self.tmp, 0o644)
            # Verify BEFORE the publish: a bad write must never
            # reach the published path.
            _check_file(self.tmp, data)
            os.replace(self.tmp, self.final)
            os.chmod(self.final, 0o644)
            _sync_dir(self.out_dir)
        finally:
            # Never leave our tmp behind, even on failure.
            try:
                os.unlink(self.tmp)
            except OSError:
                pass

    def confirm(self, data):
        """Post-publish check: the grader's file must be exact.

        The published file is checked again for regular-file type,
        exact size, exact bytes and mode 0644, and the run confirms
        its own tmp file is gone, so no stray tmp can be mistaken
        for output.
        """
        _check_file(self.final, data)
        if os.path.lexists(self.tmp):
            raise ValueError("tmp file %s still exists after publish" % self.tmp)


def main():
    check_line(LINE)
    data = (LINE + "\n").encode("utf-8")
    publisher = AtomicPublisher(output_dir())
    publisher.prepare()
    publisher.publish(data)
    publisher.confirm(data)


if __name__ == "__main__":
    main()
