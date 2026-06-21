from __future__ import annotations

from app.services.roadmap_import import parse_roadmap_markdown

SAMPLE = """# 07 — APIs & Backend Engineering Roadmap

## Resources

### YouTube
- Search: "FastAPI crash course"

## Phase 1: HTTP & REST Fundamentals (Week 1, Days 1-3)

### Concepts
- HTTP methods: GET, POST
- Status codes: 200, 404

### URL Design

## Phase 2: FastAPI Basics (Week 1-2)

### Setup
- Install fastapi

```python
# This is a code comment, NOT a heading
## Neither is this
app = FastAPI()
```

### Key Concepts
- Pydantic models
"""


def test_title_strips_number_prefix() -> None:
    parsed = parse_roadmap_markdown(SAMPLE)
    assert parsed.title == "APIs & Backend Engineering Roadmap"


def test_phase_prefix_and_duration_parsed() -> None:
    parsed = parse_roadmap_markdown(SAMPLE)
    names = [(p.name, p.duration_label) for p in parsed.phases]
    assert ("Resources", None) in names
    assert ("HTTP & REST Fundamentals", "Week 1, Days 1-3") in names
    assert ("FastAPI Basics", "Week 1-2") in names


def test_h3_and_bullets_are_topics() -> None:
    parsed = parse_roadmap_markdown(SAMPLE)
    phase1 = next(p for p in parsed.phases if p.name == "HTTP & REST Fundamentals")
    assert "Concepts" in phase1.topics
    assert "HTTP methods: GET, POST" in phase1.topics
    assert "URL Design" in phase1.topics


def test_code_block_contents_ignored() -> None:
    parsed = parse_roadmap_markdown(SAMPLE)
    all_topics = [t for p in parsed.phases for t in p.topics]
    assert "app = FastAPI()" not in all_topics
    # The '## Neither is this' inside the fence must not become a phase.
    assert all(p.name != "Neither is this" for p in parsed.phases)


def test_bullets_before_phase_go_to_overview() -> None:
    md = "# Title\n\n- orphan topic\n\n## Real Phase\n- a\n"
    parsed = parse_roadmap_markdown(md)
    overview = next(p for p in parsed.phases if p.name == "Overview")
    assert "orphan topic" in overview.topics


def test_empty_markdown_has_fallback_title() -> None:
    parsed = parse_roadmap_markdown("")
    assert parsed.title == "Untitled Roadmap"
    assert parsed.phases == []
