"""Pure markdown roadmap parser.

Format (per spec and the real docs in ``progress_tracker/docs``):
- ``#``  = roadmap title (a leading "NN — " numbering prefix is stripped).
- ``##`` = phase. A leading "Phase N:" is stripped and a trailing "(duration)"
  is parsed out into ``duration_label``.
- ``###`` headings and ``- `` bullets = topics under the current phase.

Fenced code blocks (``` ... ```) are skipped so ``#`` comments inside example
code are never mistaken for headings. Bullets appearing before the first phase
go into a synthetic "Overview" phase.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_TITLE_NUM_PREFIX = re.compile(r"^\d+\s*[—–-]\s*")
_PHASE_PREFIX = re.compile(r"^Phase\s+\d+\s*:\s*", re.IGNORECASE)
_TRAILING_PAREN = re.compile(r"^(?P<name>.*?)\s*\((?P<dur>[^()]*)\)\s*$")
_BULLET = re.compile(r"^[-*]\s+(?P<text>.+)$")


@dataclass
class ParsedPhase:
    name: str
    duration_label: str | None = None
    topics: list[str] = field(default_factory=list)


@dataclass
class ParsedRoadmap:
    title: str
    phases: list[ParsedPhase] = field(default_factory=list)


def _parse_phase_heading(text: str) -> tuple[str, str | None]:
    text = _PHASE_PREFIX.sub("", text.strip())
    match = _TRAILING_PAREN.match(text)
    if match:
        return match.group("name").strip(), match.group("dur").strip() or None
    return text.strip(), None


def parse_roadmap_markdown(markdown: str) -> ParsedRoadmap:
    title: str | None = None
    phases: list[ParsedPhase] = []
    current: ParsedPhase | None = None
    in_code = False

    def ensure_phase() -> ParsedPhase:
        nonlocal current
        if current is None:
            current = ParsedPhase(name="Overview")
            phases.append(current)
        return current

    for raw in markdown.splitlines():
        stripped = raw.strip()

        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_code = not in_code
            continue
        if in_code or not stripped:
            continue

        if stripped.startswith("### "):
            ensure_phase().topics.append(stripped[4:].strip())
        elif stripped.startswith("## "):
            name, duration = _parse_phase_heading(stripped[3:])
            current = ParsedPhase(name=name, duration_label=duration)
            phases.append(current)
        elif stripped.startswith("# "):
            if title is None:
                title = _TITLE_NUM_PREFIX.sub("", stripped[2:].strip()).strip()
        else:
            bullet = _BULLET.match(stripped)
            if bullet:
                topic = bullet.group("text").strip()
                if topic:
                    ensure_phase().topics.append(topic)

    return ParsedRoadmap(title=title or "Untitled Roadmap", phases=phases)
