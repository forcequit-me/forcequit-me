"""Merge ascii/art.txt + ascii/panel.txt into the README block between the
ascii:start / ascii:end markers. Run: python ascii/build.py

Paste new art into art.txt, edit fields in panel.txt, run this. Nothing else.
"""
import sys
from pathlib import Path

GAP = 6  # spaces between art and panel
HERE = Path(__file__).parent
README = HERE.parent / "README.md"
START, END = "<!-- ascii:start -->", "<!-- ascii:end -->"


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
    block = merge(read_lines(HERE / "art.txt"), read_lines(HERE / "panel.txt"))
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
    print("ok")


if __name__ == "__main__":
    check() if "--check" in sys.argv else main()
