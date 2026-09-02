#!/usr/bin/env python3
# claims_check.py - the release claims table checker.
#
# WHAT IT IS. A pure function of (claims file bytes) -> a refusal list and
# an exit code. It is the mechanical half of the caveat
# binding and section 3.4's anti-cherrypick law: the thing that makes
# "a row missing any field does not publish" an exit code rather than a
# habit. The release kill line is measured by this program's exit status.
#
# Written 2026-09-01. The rule set below is frozen and complete in
# itself; the design documents that scoped it are internal.
# Pure ASCII, LF endings, stdlib only, no clock, no random.
#
# ---------------------------------------------------------------
# CHECK-CLAIMS-1: THE FROZEN RULE SET
# ---------------------------------------------------------------
# These rules are frozen with this file. A change to any of them is
# CHECK-CLAIMS-2 in a new file, never an edit here, because a cut banked
# under CHECK-CLAIMS-1 must stay reproducible forever.
#
# X0 BYTES. The file decodes as strict ASCII, uses LF only, carries no
#    trailing whitespace and no em dash. Any violation is a refusal.
#
# X1 STRUCTURE. The file is a sequence of BLOCKS in the frozen ledger
#    block format: "KEY: VALUE" lines,
#    RFC822-style folding of continuation lines (leading space, not
#    "UPPERCASE_KEY:", not "---"), each block closed by a line that is
#    exactly "---", exactly one blank line between blocks. Comment lines
#    begin with "#" at column 0 and are ignored outside blocks.
#
# X2 COMPLETENESS (bar b: "a number outside a complete row"). Every ROW
#    block carries every key in ROW_KEYS, non-empty. Every CLAIM block
#    carries every key in CLAIM_KEYS, non-empty. A block missing a key,
#    or carrying an unknown key, is refused BY NAME. This is the
#    mechanization of C7 section 3.1: "A row missing any field does not
#    publish."
#
# X3 CAVEAT (bar a). CAVEAT is non-empty after normalization, is not a
#    placeholder token (TBD, TODO, NONE, N/A, -, ., NA), is at least
#    MIN_CAVEAT_CHARS characters, and CAVEAT_SOURCE names a receipt
#    document and a section. A number and its caveat travel as one
#    inseparable string in every generated surface.
#
# X4 WORST IN LEG (bar c). Every block that publishes a COST ratio
#    declares its LEG and its COST_SPREAD (every ratio observed in that
#    leg, space separated). The published ratio must equal the maximum of
#    COST_SPREAD. A published best-of is refused.
#    Rows whose COST is the literal token BASELINE are exempt and must
#    have COST_SPREAD BASELINE.
#
# X5 ACCT PAIRING. Frozen rule R-1:
#    "A row that publishes one without the other is incomplete under
#    P07's checker." A ROW whose EXPOSURE_ACCT_RESIDENCY is a number must
#    carry a numeric EXPOSURE_ACCT_HELD and the reverse. An UNMEASURED
#    reading on one side requires an UNMEASURED reading on the other.
#
# X6 THROUGHPUT LABEL. By convention, a throughput figure is labelled
#    "tok/s eval" or "tok/s decode" and the two never share an unlabelled
#    column. C3-j: every tok/s figure states its regime. THROUGHPUT must
#    match THROUGHPUT_RE and name a regime from REGIMES.
#
# X7 DEVICE. By rule: "DEVICE IS NOT OPTIONAL AND THREAD COUNT IS
#    THE REASON." DEVICE must name box, cpu, ram, threads, nice and gpu.
#    STORE and STORE_OBS are H-BOX additions and are
#    required on any ROW whose mechanism moved model bytes.
#
# X8 ARITHMETIC. Where a row states tokens, wall clock and tok/s, tok/s
#    must equal tokens/wall to ROUND_TOKS decimal places. Where a row
#    states an exposure with its denominator terms, the quotient must
#    equal the stated exposure to ROUND_EXP decimal places, and the terms
#    must sum to the stated denominator exactly. The checker recomputes;
#    it never trusts.
#
# X9 UNMEASURED. The literal token UNMEASURED may stand in for a field
#    the row's receipt does not carry, and only when followed by a
#    parenthesized reason. A bare UNMEASURED is a refusal. An UNMEASURED
#    field may not be quoted as a number anywhere.
#
# X10 CITATION. RECEIPT names a repo-relative path. COMMIT is 40 lowercase
#    hex, or the literal "NOT-ON-THIS-BRANCH <40hex>" which is ACCEPTED by
#    the table check and REPORTED as a citation hazard, because the cut
#    gate G4 resolves citations from the cut alone and a
#    commit that is not an ancestor of the cut's HEAD will not resolve
#    there. The table checker does not touch git; it reports the marker.
#
# X11 SURFACE (--surface). Every numeric token in a generated surface file
#    must be declared somewhere in the claims table. A numeric token is a
#    maximal run of [0-9.] that is not adjacent to a letter, underscore or
#    hyphen on either side (so "OB1B-KNEE-1" contributes nothing and
#    "K=8" contributes "8"). This is the downstream half of bar (b) and
#    the measurement for K12.
#
# EXIT. 0 when every rule holds. 1 when any rule is refused. 2 on a usage
# or I/O error. Every refusal prints one line:
#   REFUSE <rule> <block-id>: <reason>
# and the refusals are printed in file order, then by rule id.

import re
import sys

ROW_KEYS = [
    "ID", "KIND", "LEG", "MODEL", "CONFIG", "DEVICE", "STORE", "STORE_OBS",
    "IDENTITY", "EXPOSURE_ACCT_RESIDENCY", "EXPOSURE_ACCT_HELD",
    "EXPOSURE_RSS", "THROUGHPUT", "COST", "COST_SPREAD", "CAVEAT",
    "CAVEAT_SOURCE", "RECEIPT", "COMMIT",
]

CLAIM_KEYS = [
    "ID", "KIND", "LEG", "WHAT", "VALUE", "DERIVATION", "COST", "COST_SPREAD",
    "CAVEAT", "CAVEAT_SOURCE", "RECEIPT", "COMMIT",
]

PLACEHOLDERS = ("tbd", "todo", "none", "n/a", "na", "-", ".", "")
MIN_CAVEAT_CHARS = 24
ROUND_TOKS = 2
ROUND_EXP = 6
REGIMES = ("batch-prefill", "decode", "mixed")

THROUGHPUT_RE = re.compile(
    r"^(?P<toks>[0-9]+\.[0-9]+) tok/s (?P<label>eval|decode); "
    r"regime (?P<regime>[a-z-]+) B=(?P<b>[0-9]+); "
    r"tokens (?P<tokens>[0-9]+); wall_s (?P<wall>[0-9]+\.[0-9]+); "
    r"ms_per_token (?P<mspt>[0-9]+\.[0-9]+)$"
)

DEVICE_RE = re.compile(
    r"^box (?P<box>\S+); cpu (?P<cpu>[^;]+); ram_mb (?P<ram>[0-9]+|UNSTATED); "
    r"threads (?P<threads>[0-9]+); nice (?P<nice>[0-9]+); gpu (?P<gpu>.+)$"
)
DEVICE_GAP_NOTE = "DEVICE GAP"

EXPOSURE_RE = re.compile(
    r"^(?P<val>[0-9]+\.[0-9]+) = (?P<n>[0-9]+) / (?P<den>[0-9]+) "
    r"\[(?P<terms>[0-9 +]+)\]$"
)

COST_RE = re.compile(
    r"^(?P<ratio>[0-9]+\.[0-9]+)x (?P<stat>[^;]+); "
    r"baseline (?P<base>.+)$"
)

MODEL_RE = re.compile(
    r"^(?P<name>[^;]+); bytes (?P<bytes>[0-9]+); sha256 (?P<sha>.+)$")

RSS_RE = re.compile(
    r"^(?P<val>[0-9]+\.[0-9]+); peak RSS (?P<peak>[0-9]+) bytes(?P<note>.*)$")

UNMEASURED_RE = re.compile(r"^UNMEASURED \([^()]+\)$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
NOT_ON_BRANCH_RE = re.compile(r"^NOT-ON-THIS-BRANCH [0-9a-f]{40}$")
CAVEAT_SOURCE_RE = re.compile(r"^\S+\.md (s|section )[0-9A-Za-z.,() -]+$")
NUMTOK_RE = re.compile(r"(?<![A-Za-z0-9_.-])([0-9][0-9.]*)x?(?![A-Za-z0-9_.-])")
EM_DASH_UTF8 = b"\xe2\x80\x94"


class Refusal(object):
    def __init__(self, rule, bid, reason, order):
        self.rule = rule
        self.bid = bid
        self.reason = reason
        self.order = order

    def line(self):
        return "REFUSE %s %s: %s" % (self.rule, self.bid, self.reason)

    def key(self):
        return (self.order, self.rule, self.bid)


def read_bytes(path):
    fh = open(path, "rb")
    try:
        return fh.read()
    finally:
        fh.close()


def check_bytes(raw, refusals):
    """X0. Returns decoded text, or None when the bytes are unusable."""
    if b"\r" in raw:
        refusals.append(Refusal("X0", "<file>", "CR byte present; LF only", -1))
    if EM_DASH_UTF8 in raw:
        refusals.append(Refusal("X0", "<file>", "em dash present", -1))
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        refusals.append(Refusal("X0", "<file>", "non-ASCII byte: %s" % exc, -1))
        return None
    for i, line in enumerate(text.split("\n")):
        if line != line.rstrip():
            refusals.append(
                Refusal("X0", "<file>", "trailing whitespace on line %d" % (i + 1), -1))
    return text


def parse_blocks(text, refusals):
    """X1. Returns a list of (order, lineno, dict) with keys in file order."""
    blocks = []
    cur = None
    curkeys = None
    lastkey = None
    startline = 0
    order = 0
    for i, line in enumerate(text.split("\n")):
        lineno = i + 1
        if cur is None:
            if line == "" or line.startswith("#"):
                continue
            if line == "---":
                refusals.append(
                    Refusal("X1", "<line %d>" % lineno, "block terminator outside a block", order))
                continue
            cur = {}
            curkeys = []
            lastkey = None
            startline = lineno
        if line == "---":
            blocks.append((order, startline, cur, curkeys))
            order += 1
            cur = None
            curkeys = None
            lastkey = None
            continue
        if line == "":
            refusals.append(
                Refusal("X1", "<line %d>" % startline, "blank line inside a block", order))
            continue
        m = re.match(r"^([A-Z][A-Z0-9_]*): ?(.*)$", line)
        if m:
            key = m.group(1)
            if key in cur:
                refusals.append(
                    Refusal("X1", "<line %d>" % lineno, "duplicate key %s" % key, order))
            cur[key] = m.group(2).strip()
            curkeys.append(key)
            lastkey = key
            continue
        if line.startswith(" ") and lastkey is not None:
            cur[lastkey] = (cur[lastkey] + " " + line.strip()).strip()
            continue
        refusals.append(
            Refusal("X1", "<line %d>" % lineno, "line is neither a KEY line, a "
                    "continuation (leading space) nor a terminator", order))
    if cur is not None:
        refusals.append(
            Refusal("X1", "<line %d>" % startline, "block never closed by ---", order))
    return blocks


def is_unmeasured(value):
    return value.startswith("UNMEASURED")


def check_unmeasured(rule, bid, key, value, refusals, order):
    """X9."""
    if not is_unmeasured(value):
        return False
    if not UNMEASURED_RE.match(value):
        refusals.append(
            Refusal("X9", bid, "%s: bare UNMEASURED; a reason in parentheses "
                    "is required" % key, order))
    return True


def check_block(order, startline, blk, keys, refusals):
    bid = blk.get("ID", "<line %d>" % startline)
    kind = blk.get("KIND", "")
    if kind == "ROW":
        required = ROW_KEYS
    elif kind == "CLAIM":
        required = CLAIM_KEYS
    else:
        refusals.append(
            Refusal("X2", bid, "KIND must be ROW or CLAIM, got %r" % kind, order))
        return

    # X2 completeness and unknown keys.
    for key in required:
        if key not in blk:
            refusals.append(Refusal("X2", bid, "missing key %s" % key, order))
        elif blk[key].strip() == "" and key != "CAVEAT":
            # CAVEAT emptiness belongs to X3 alone, so that a fixture built to
            # test the caveat binding is refused for the caveat binding and not
            # incidentally for completeness as well.
            refusals.append(Refusal("X2", bid, "empty value for %s" % key, order))
    for key in keys:
        if key not in required:
            refusals.append(Refusal("X2", bid, "unknown key %s" % key, order))

    # X3 caveat.
    cav = blk.get("CAVEAT", "")
    if cav.strip().lower() in PLACEHOLDERS:
        refusals.append(
            Refusal("X3", bid, "CAVEAT is empty or a placeholder (%r)" % cav, order))
    elif len(cav.strip()) < MIN_CAVEAT_CHARS:
        refusals.append(
            Refusal("X3", bid, "CAVEAT is %d chars, under the %d minimum"
                    % (len(cav.strip()), MIN_CAVEAT_CHARS), order))
    cavsrc = blk.get("CAVEAT_SOURCE", "")
    if cavsrc and not CAVEAT_SOURCE_RE.match(cavsrc):
        refusals.append(
            Refusal("X3", bid, "CAVEAT_SOURCE must name a .md receipt and a "
                    "section, got %r" % cavsrc, order))

    # X10 citation.
    commit = blk.get("COMMIT", "")
    if commit and not (COMMIT_RE.match(commit) or NOT_ON_BRANCH_RE.match(commit)):
        refusals.append(
            Refusal("X10", bid, "COMMIT is neither 40-hex nor "
                    "'NOT-ON-THIS-BRANCH <40hex>', got %r" % commit, order))

    # X9 on every field.
    for key in required:
        if key in blk:
            check_unmeasured("X9", bid, key, blk[key], refusals, order)

    if kind == "ROW":
        check_row_specific(order, blk, bid, refusals)


def check_row_specific(order, blk, bid, refusals):
    # X7 device.
    dev = blk.get("DEVICE", "")
    if dev and not is_unmeasured(dev):
        if not DEVICE_RE.match(dev):
            refusals.append(
                Refusal("X7", bid, "DEVICE must read 'box <b>; cpu <c>; ram_mb "
                        "<n|UNSTATED>; threads <n>; nice <n>; gpu <g>', got %r"
                        % dev, order))
        elif "UNSTATED" in dev and DEVICE_GAP_NOTE not in blk.get("CAVEAT", ""):
            refusals.append(
                Refusal("X7", bid, "DEVICE carries an UNSTATED subfield, so the "
                        "CAVEAT must contain the literal %r" % DEVICE_GAP_NOTE,
                        order))

    # X6 throughput label and regime.
    thr = blk.get("THROUGHPUT", "")
    m = None
    if thr and not is_unmeasured(thr):
        m = THROUGHPUT_RE.match(thr)
        if not m:
            refusals.append(
                Refusal("X6", bid, "THROUGHPUT must read '<x.xx> tok/s "
                        "eval|decode; regime <r> B=<n>; tokens <n>; wall_s <x>; "
                        "ms_per_token <x>' (OB5-024 label, C3-j regime), got %r"
                        % thr, order))
        elif m.group("regime") not in REGIMES:
            refusals.append(
                Refusal("X6", bid, "regime %r is not one of %s"
                        % (m.group("regime"), ", ".join(REGIMES)), order))

    # X8 arithmetic, throughput limb.
    if m is not None:
        tokens = float(m.group("tokens"))
        wall = float(m.group("wall"))
        stated = float(m.group("toks"))
        recomputed = round(tokens / wall, ROUND_TOKS)
        if round(stated, ROUND_TOKS) != recomputed:
            refusals.append(
                Refusal("X8", bid, "tok/s %s does not equal tokens/wall_s = %s "
                        "at %d dp" % (m.group("toks"), ("%%.%df" % ROUND_TOKS)
                                      % recomputed, ROUND_TOKS), order))
        mspt = float(m.group("mspt"))
        rec_mspt = round(wall * 1000.0 / tokens, 3)
        if round(mspt, 3) != rec_mspt:
            refusals.append(
                Refusal("X8", bid, "ms_per_token %s does not equal "
                        "wall_s*1000/tokens = %.3f" % (m.group("mspt"), rec_mspt),
                        order))

    # X8 arithmetic, RSS limb: exposure_rss must equal model bytes / peak RSS.
    model = blk.get("MODEL", "")
    mm = MODEL_RE.match(model) if model and not is_unmeasured(model) else None
    if model and not is_unmeasured(model) and mm is None:
        refusals.append(
            Refusal("X8", bid, "MODEL must read '<file>; bytes <n>; sha256 <h>', "
                    "got %r" % model, order))
    rss = blk.get("EXPOSURE_RSS", "")
    if rss and not is_unmeasured(rss):
        rm = RSS_RE.match(rss)
        if not rm:
            refusals.append(
                Refusal("X8", bid, "EXPOSURE_RSS must read '<x.xxxxxx>; peak RSS "
                        "<n> bytes[ note]', got %r" % rss, order))
        elif mm is not None:
            recomputed = round(int(mm.group("bytes")) / float(rm.group("peak")),
                               ROUND_EXP)
            if round(float(rm.group("val")), ROUND_EXP) != recomputed:
                refusals.append(
                    Refusal("X8", bid, "EXPOSURE_RSS: %s does not equal model "
                            "bytes / peak RSS = %s at %d dp"
                            % (rm.group("val"),
                               ("%%.%df" % ROUND_EXP) % recomputed, ROUND_EXP),
                            order))

    # X5 ACCT pairing, and X8 arithmetic on both limbs.
    res = blk.get("EXPOSURE_ACCT_RESIDENCY", "")
    held = blk.get("EXPOSURE_ACCT_HELD", "")
    res_num = bool(res) and not is_unmeasured(res)
    held_num = bool(held) and not is_unmeasured(held)
    if res_num != held_num:
        refusals.append(
            Refusal("X5", bid, "ACCT pairing (SUMMARY CONFLICT 1 RULE R-1): a row "
                    "publishes ACCT_residency and ACCT_held together or not at "
                    "all; residency=%s held=%s"
                    % ("number" if res_num else "unmeasured",
                       "number" if held_num else "unmeasured"), order))
    for key in ("EXPOSURE_ACCT_RESIDENCY", "EXPOSURE_ACCT_HELD"):
        val = blk.get(key, "")
        if not val or is_unmeasured(val):
            continue
        em = EXPOSURE_RE.match(val)
        if not em:
            refusals.append(
                Refusal("X8", bid, "%s must read '<x.xxxxxx> = <N> / <ACCT> "
                        "[<term> + <term> + ...]', got %r" % (key, val), order))
            continue
        terms = [int(t) for t in em.group("terms").split("+")]
        den = int(em.group("den"))
        if sum(terms) != den:
            refusals.append(
                Refusal("X8", bid, "%s: denominator terms sum to %d, not the "
                        "stated %d" % (key, sum(terms), den), order))
        recomputed = round(int(em.group("n")) / float(den), ROUND_EXP)
        if round(float(em.group("val")), ROUND_EXP) != recomputed:
            refusals.append(
                Refusal("X8", bid, "%s: %s does not equal N/ACCT = %s at %d dp"
                        % (key, em.group("val"),
                           ("%%.%df" % ROUND_EXP) % recomputed, ROUND_EXP), order))


def check_cost(blocks, refusals):
    """X4. Worst in leg, across every block that publishes a cost ratio."""
    legs = {}
    for order, startline, blk, _keys in blocks:
        bid = blk.get("ID", "<line %d>" % startline)
        cost = blk.get("COST", "")
        spread = blk.get("COST_SPREAD", "")
        if not cost:
            continue
        if cost == "BASELINE":
            if spread != "BASELINE":
                refusals.append(
                    Refusal("X4", bid, "COST BASELINE requires COST_SPREAD "
                            "BASELINE, got %r" % spread, order))
            continue
        if is_unmeasured(cost):
            if not is_unmeasured(spread):
                refusals.append(
                    Refusal("X4", bid, "an UNMEASURED COST requires an "
                            "UNMEASURED COST_SPREAD, got %r" % spread, order))
            continue
        cm = COST_RE.match(cost)
        if not cm:
            refusals.append(
                Refusal("X4", bid, "COST must read '<x.xxxx>x <statistic>; "
                        "baseline <what>', got %r" % cost, order))
            continue
        tokens_ = spread.split()
        try:
            values = [float(t) for t in tokens_]
        except ValueError:
            refusals.append(
                Refusal("X4", bid, "COST_SPREAD must be space-separated "
                        "ratios, got %r" % spread, order))
            continue
        if not values:
            refusals.append(Refusal("X4", bid, "COST_SPREAD is empty", order))
            continue
        worst = tokens_[values.index(max(values))]
        published = float(cm.group("ratio"))
        if published not in values:
            refusals.append(
                Refusal("X4", bid, "published cost %s is not a member of its "
                        "own COST_SPREAD %s" % (cm.group("ratio"), spread), order))
            continue
        if published != max(values):
            refusals.append(
                Refusal("X4", bid, "published cost %s is not the worst in its "
                        "leg; the worst observed is %s (C7 s3.4, the "
                        "anti-cherrypick law)"
                        % (cm.group("ratio"), worst), order))
        leg = blk.get("LEG", "")
        legs.setdefault(leg, []).append((bid, order, tuple(sorted(values))))
    for leg in sorted(legs):
        seen = set(entry[2] for entry in legs[leg])
        if len(seen) > 1:
            for bid, order, _vals in legs[leg]:
                refusals.append(
                    Refusal("X4", bid, "LEG %s carries more than one distinct "
                            "COST_SPREAD; a leg has one spread" % leg, order))


def declared_numbers(blocks):
    out = set()
    for _order, _startline, blk, keys in blocks:
        for key in keys:
            for tok in NUMTOK_RE.findall(blk[key]):
                out.add(tok.rstrip("."))
    return out


def check_surface(path, blocks, refusals):
    """X11."""
    raw = read_bytes(path)
    text = check_bytes(raw, refusals)
    if text is None:
        return
    declared = declared_numbers(blocks)
    for i, line in enumerate(text.split("\n")):
        for tok in NUMTOK_RE.findall(line):
            tok = tok.rstrip(".")
            if tok and tok not in declared:
                refusals.append(
                    Refusal("X11", "%s:%d" % (path, i + 1),
                            "number %r appears in a surface but is not declared "
                            "in the claims table" % tok, 10 ** 6 + i))


def report_hazards(blocks, out):
    hazards = []
    for _order, startline, blk, _keys in blocks:
        bid = blk.get("ID", "<line %d>" % startline)
        commit = blk.get("COMMIT", "")
        if NOT_ON_BRANCH_RE.match(commit):
            hazards.append(
                "HAZARD X10 %s: %s cited at %s, which is not on this branch; "
                "gate G4 resolves citations from the cut alone"
                % (bid, blk.get("RECEIPT", "<no receipt>"), commit.split()[1]))
    for line in sorted(hazards):
        out.write(line + "\n")
    return len(hazards)


def main(argv):
    # LF on stdout regardless of platform, so a banked runlog is byte-stable
    # across the boxes this house runs on. Guarded: reconfigure lands in 3.7
    # and this program is meant to keep running on older interpreters.
    try:
        sys.stdout.reconfigure(newline=chr(10))
        sys.stderr.reconfigure(newline=chr(10))
    except AttributeError:
        pass
    if len(argv) < 2:
        sys.stderr.write(
            "usage: claims_check.py CLAIMS_FILE [--surface FILE ...]\n")
        return 2
    path = argv[1]
    surfaces = []
    i = 2
    while i < len(argv):
        if argv[i] == "--surface" and i + 1 < len(argv):
            surfaces.append(argv[i + 1])
            i += 2
            continue
        sys.stderr.write("usage: claims_check.py CLAIMS_FILE "
                         "[--surface FILE ...]\n")
        return 2
    try:
        raw = read_bytes(path)
    except IOError as exc:
        sys.stderr.write("cannot read %s: %s\n" % (path, exc))
        return 2

    refusals = []
    text = check_bytes(raw, refusals)
    blocks = []
    if text is not None:
        blocks = parse_blocks(text, refusals)
        for order, startline, blk, keys in blocks:
            check_block(order, startline, blk, keys, refusals)
        check_cost(blocks, refusals)
        for surface in surfaces:
            try:
                check_surface(surface, blocks, refusals)
            except IOError as exc:
                sys.stderr.write("cannot read surface %s: %s\n" % (surface, exc))
                return 2

    out = sys.stdout
    out.write("claims_check.py CHECK-CLAIMS-1\n")
    out.write("file: %s\n" % path)
    out.write("blocks: %d\n" % len(blocks))
    out.write("surfaces: %d\n" % len(surfaces))
    for ref in sorted(refusals, key=lambda r: r.key()):
        out.write(ref.line() + "\n")
    nhaz = report_hazards(blocks, out)
    out.write("refusals: %d\n" % len(refusals))
    out.write("hazards: %d\n" % nhaz)
    out.write("verdict: %s\n" % ("REFUSED" if refusals else "ACCEPTED"))
    return 1 if refusals else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
