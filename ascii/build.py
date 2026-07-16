"""Merge ascii/art.txt + ascii/panel.txt into the README block between the
ascii:start / ascii:end markers. Run: python ascii/build.py

Paste new art into art.txt, edit fields in panel.txt, run this. Nothing else.

Art is placed as authored: dead rows trimmed, and shrunk only if wider than
MAX_COLS. Its proportions are never changed.

Pass --squash for art straight out of an image-to-ASCII converter that didn't
correct for character shape (1 char = 1 pixel, so it comes out ~2x too tall).
Art that already looks right in a terminal does NOT want --squash.
"""
import sys
from pathlib import Path

MAX_COLS = 76    # 76 + GAP + 45-wide panel = 127, about the width GitHub shows
CHAR_AR = 0.5    # char width / height
GAP = 6          # spaces between art and panel
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


def rescale(art, cols, squash=False):
    """Resample the char grid to `cols` wide. Rows scale by the same factor, so
    the art keeps its proportions - unless squash=True, which halves them to
    correct converter output that assumed square pixels."""
    src_rows = len(art)
    src_cols = max(len(l) for l in art)
    grid = [l.ljust(src_cols) for l in art]
    rows = max(1, round(cols * (CHAR_AR if squash else 1.0) * src_rows / src_cols))
    out = []
    for y in range(rows):
        y0, y1 = y * src_rows // rows, max(y * src_rows // rows + 1, (y + 1) * src_rows // rows)
        line = ""
        for x in range(cols):
            x0, x1 = x * src_cols // cols, max(x * src_cols // cols + 1, (x + 1) * src_cols // cols)
            cells = [grid[j][i] for j in range(y0, y1) for i in range(x0, x1)]
            ink = sum(c != " " for c in cells)
            line += max(set(cells), key=cells.count) if ink * 2 >= len(cells) else " "
        out.append(line.rstrip())
    return out


def merge(art, panel, gap=GAP):
    """Art on the left, panel vertically centered on the right."""
    width = max((len(l) for l in art), default=0)
    off = max(0, (len(art) - len(panel)) // 2)
    rows = max(len(art), off + len(panel))
    out = []
    for i in range(rows):
        left = art[i] if i < len(art) else ""
        j = i - off
        right = panel[j] if 0 <= j < len(panel) else ""
        out.append((left.ljust(width) + " " * gap + right).rstrip())
    return "\n".join(out)


def read_lines(path):
    return path.read_text(encoding="utf-8").rstrip("\n").split("\n")


def main():
    art = trim(read_lines(HERE / "art.txt"))
    squash = "--squash" in sys.argv
    if squash or max(len(l) for l in art) > MAX_COLS:
        art = rescale(art, MAX_COLS, squash=squash)
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

    square = ["#" * 40] * 40
    r = rescale(square, cols=20)                    # proportions kept: 40x40 -> 20x20
    assert (len(r), len(r[0])) == (20, 20), (len(r), len(r[0]))
    assert all(set(l) == {"#"} for l in r), "solid block must stay solid"
    r = rescale(square, cols=20, squash=True)       # squash halves the rows
    assert len(r) == 10, len(r)
    assert rescale([" " * 40] * 40, cols=20) == [""] * 20, "blank must stay blank"

    # trim: uniform bands go, indented shape rows stay
    assert trim(["####", "    ", "#  #", "####"]) == ["#  #"]
    assert trim(["  ##  ", "#    #", "  ##  "]) == ["  ##", "#    #", "  ##"]
    assert trim(["#  #"]) == ["#  #"]
    print("ok")


if __name__ == "__main__":
    check() if "--check" in sys.argv else main()
