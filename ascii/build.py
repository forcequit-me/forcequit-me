"""Merge ascii/art.txt + ascii/panel.txt into the README block between the
ascii:start / ascii:end markers. Run: python ascii/build.py

Paste new art into art.txt, edit fields in panel.txt, run this. Nothing else.

Art is trimmed of dead rows and refitted to MAX_COLS, with rows derived so it
holds its intended shape in GitHub's renderer. A circle stays a circle.

Pass --squash for art straight out of an image-to-ASCII converter that didn't
correct for character shape (1 char = 1 source pixel).
"""
import sys
from pathlib import Path

MAX_COLS = 72    # 72 + GAP + 45-wide panel = 123; 76 rendered a touch too wide
GAP = 6          # spaces between art and panel

# Char cell width/height where the art was authored vs where it gets rendered.
# GitHub is font advance (~0.6em) over line-height (1.45em) = 0.41; measured
# ~0.39 off a real screenshot, so 0.40. Calibration knob: if art still reads
# stretched on the page, nudge this, don't touch the math.
GITHUB_AR = 0.40

# The cell aspect the art in art.txt was DRAWN FOR. Get this wrong and the art
# renders stretched. 0.5 is the common default. If the art's bounding box is
# meant to read square (a circular logo), use its own srcRows/srcCols - for the
# current 50x27 art that is 27/50 = 0.54, which renders 50x20 and truly round.
# Override per-run with --source-ar 0.5, or --squash for raw converter output.
SOURCE_AR = 0.54

HERE = Path(__file__).parent
README = HERE.parent / "README.md"
START, END = "<!-- ascii:start -->", "<!-- ascii:end -->"


def trim(art):
    """Drop leading/trailing rows carrying no shape: uniform edge to edge, all
    blank or all solid. Tested at full width - '   ####   ' is shape, not dead
    space, so it stays."""
    width = max((len(l) for l in art), default=0)
    art = [l.ljust(width) for l in art]
    while art and len(set(art[0])) <= 1: art.pop(0)
    while art and len(set(art[-1])) <= 1: art.pop()
    return [l.rstrip() for l in art]


def rescale(art, cols, source_ar=SOURCE_AR):
    """Resample the char grid to `cols` wide, picking the row count that makes
    the art's intended shape survive GitHub's character cells.

    The art looks the way its author meant at aspect `source_ar`, i.e. it wants
    to display (src_cols * source_ar) wide by src_rows tall. Solve for the rows
    that reproduce that shape at GITHUB_AR."""
    src_rows = len(art)
    src_cols = max(len(l) for l in art)
    grid = [l.ljust(src_cols) for l in art]
    rows = max(1, round(cols * GITHUB_AR * src_rows / (src_cols * source_ar)))

    def pick(n, size, count):
        """Source index for output cell n: sample the middle of its span. Even
        at the edges, so the first and last row/col of the art always survive -
        bucket-averaging silently ate the bottom of a circle."""
        return min(size - 1, int((n + 0.5) * size / count))

    out = []
    for y in range(rows):
        row = grid[pick(y, src_rows, rows)]
        out.append("".join(row[pick(x, src_cols, cols)] for x in range(cols)).rstrip())
    return out


def merge(art, panel, gap=GAP):
    """Art left, panel right, the shorter of the two centered against the taller."""
    width = max((len(l) for l in art), default=0)
    art_off = max(0, (len(panel) - len(art)) // 2)
    panel_off = max(0, (len(art) - len(panel)) // 2)
    rows = max(art_off + len(art), panel_off + len(panel))
    out = []
    for i in range(rows):
        a, p = i - art_off, i - panel_off
        left = art[a] if 0 <= a < len(art) else ""
        right = panel[p] if 0 <= p < len(panel) else ""
        out.append((left.ljust(width) + " " * gap + right).rstrip())
    return "\n".join(out)


def read_lines(path):
    return path.read_text(encoding="utf-8").rstrip("\n").split("\n")


def main():
    art = trim(read_lines(HERE / "art.txt"))
    source_ar = SOURCE_AR
    if "--squash" in sys.argv:
        source_ar = 1.0
    elif "--source-ar" in sys.argv:
        source_ar = float(sys.argv[sys.argv.index("--source-ar") + 1])
    if "--raw" not in sys.argv:
        # Never widen past the source: upscaling invents no detail, it just
        # duplicates rows and columns into visible stair-steps.
        cols = min(MAX_COLS, max(len(l) for l in art))
        art = rescale(art, cols, source_ar)
    block = merge(art, read_lines(HERE / "panel.txt"))
    src = README.read_text(encoding="utf-8")
    if START not in src or END not in src:
        sys.exit(f"markers {START} / {END} not found in README.md")
    head, rest = src.split(START, 1)
    _, tail = rest.split(END, 1)
    new = f"{head}{START}\n\n```\n{block}\n```\n\n{END}{tail}"
    README.write_text(new, encoding="utf-8", newline="\n")
    widest = max(len(l) for l in block.split("\n"))
    print(f"README.md updated - {len(block.split(chr(10)))} rows, {widest} cols wide")
    if widest > 128:
        print("warning: over ~128 cols, GitHub will scroll it sideways")


def check():
    art = ["AAA", "AAAA", "AAA", "AAA", "AAA"]
    panel = ["one", "two", "three"]
    out = merge(art, panel, gap=2).split("\n")
    assert len(out) == 5, out
    assert out[0] == "AAA", repr(out[0])          # no panel yet, padding stripped
    assert out[1] == "AAAA  one", repr(out[1])    # panel starts at centered offset
    assert out[3] == "AAA   three", repr(out[3])  # short art line padded to width
    assert all(p in "\n".join(out) for p in panel)

    # short art centers against a taller panel instead of hanging off the top
    out = merge(["AA"], ["1", "2", "3", "4", "5"], gap=2).split("\n")
    assert len(out) == 5, out
    assert out[2] == "AA  3", repr(out[2])
    assert out[0] == "    1", repr(out[0])

    square = ["#" * 40] * 40
    assert all(set(l) == {"#"} for l in rescale(square, 20, 0.5)), "solid stays solid"
    assert rescale([" " * 40] * 40, 20, 0.5) == [""] * 16, "blank stays blank"

    # The point of the whole exercise: art drawn as a circle for a 0.5 terminal
    # must still be a circle on the page. Round at GITHUB_AR means the rendered
    # box is square: cols * GITHUB_AR == rows, within a rounding row.
    circle = ["#" * 40] * 20          # 40x20 reads round at source_ar 0.5
    r = rescale(circle, 76, 0.5)
    assert abs(76 * GITHUB_AR - len(r)) <= 1, f"not round: 76x{len(r)}"

    # Converter output (1 char = 1 pixel) needs --squash to reach the same shape
    r = rescale(["#" * 40] * 40, 76, 1.0)
    assert abs(76 * GITHUB_AR - len(r)) <= 1, f"not round: 76x{len(r)}"

    # Edge rows must survive the resample, or round shapes come out flat-capped
    capped = ["  ##  ", "######", "######", "######", "######", "  ##  "]
    r = rescale(capped, 6, source_ar=6 * GITHUB_AR / 6)
    assert r[0].strip() == "##" and r[-1].strip() == "##", r

    # trim: uniform bands go, indented shape rows stay
    assert trim(["####", "    ", "#  #", "####"]) == ["#  #"]
    assert trim(["  ##  ", "#    #", "  ##  "]) == ["  ##", "#    #", "  ##"]
    assert trim(["#  #"]) == ["#  #"]
    print("ok")


if __name__ == "__main__":
    check() if "--check" in sys.argv else main()
