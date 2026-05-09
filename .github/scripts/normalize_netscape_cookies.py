from __future__ import annotations

import sys
from pathlib import Path


def decode_secret_text(text: str) -> str:
    stripped = text.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {'"', "'"}:
        stripped = stripped[1:-1]

    has_actual_layout = "\n" in stripped or "\t" in stripped
    has_escaped_layout = "\\n" in stripped or "\\t" in stripped or "\\r" in stripped

    if has_escaped_layout and not has_actual_layout:
        stripped = stripped.replace("\\r\\n", "\n")
        stripped = stripped.replace("\\n", "\n")
        stripped = stripped.replace("\\t", "\t")
        stripped = stripped.replace("\\r", "\r")
    elif "\\t" in stripped and "\t" not in stripped:
        stripped = stripped.replace("\\t", "\t")

    return stripped


def normalize_cookie_line(raw_line: str) -> str | None:
    line = raw_line.strip()
    if not line:
        return None
    if line.startswith("#"):
        return line

    parts = line.split("\t") if "\t" in line else line.split()
    if len(parts) < 7:
        return line

    return "\t".join(parts[:6] + [" ".join(parts[6:])])


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        raise SystemExit(
            "Usage: normalize_netscape_cookies.py <source> <target>"
        )

    source = Path(argv[1])
    target = Path(argv[2])
    text = decode_secret_text(source.read_text(encoding="utf-8-sig"))

    normalized_lines: list[str] = []
    for raw_line in text.splitlines():
        normalized = normalize_cookie_line(raw_line)
        if normalized is not None:
            normalized_lines.append(normalized)

    target.write_text("\n".join(normalized_lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))