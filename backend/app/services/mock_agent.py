from __future__ import annotations

from typing import List, Dict


def extract_evidence_cards(title: str, abstract: str) -> List[Dict[str, str]]:
    short = abstract[:220].strip()
    return [
        {
            "card_type": "claim",
            "title": f"Core claim from {title}",
            "content": f"This paper argues that {short or 'the proposed method improves the target task under the stated setting.'}",
        },
        {
            "card_type": "method",
            "title": f"Method summary of {title}",
            "content": "The work proposes a method pipeline involving data preparation, model design, and evaluation against baselines.",
        },
        {
            "card_type": "dataset",
            "title": f"Dataset and evaluation in {title}",
            "content": "The paper evaluates on one or more benchmark datasets and reports comparative metrics versus prior work.",
        },
        {
            "card_type": "limitation",
            "title": f"Possible limitations of {title}",
            "content": "Limitations may include narrow benchmark coverage, limited ablation, or unclear real-world generalization.",
        },
        {
            "card_type": "open_question",
            "title": f"Open questions after reading {title}",
            "content": "How well does the method generalize to different data domains, larger scales, or stronger baselines?",
        },
    ]


def compile_markdown_note(project_title: str, topic: str, papers: List[Dict], evidence_cards: List[Dict]) -> str:
    lines: List[str] = [
        f"# {project_title}",
        "",
        f"## Topic",
        topic,
        "",
        "## Key Papers",
    ]

    if not papers:
        lines.extend(["- No papers added yet.", ""])
    else:
        for paper in papers:
            lines.append(f"- **{paper['title']}** ({paper['year']}) — {paper['authors'] or 'Unknown authors'}")
        lines.append("")

    lines.extend(["## Evidence Summary", ""])
    grouped: Dict[str, List[str]] = {}
    for card in evidence_cards:
        grouped.setdefault(card["card_type"], []).append(f"- **{card['title']}**: {card['content']}")

    for section in ["claim", "method", "dataset", "limitation", "open_question"]:
        lines.append(f"### {section.replace('_', ' ').title()}")
        items = grouped.get(section, ["- No evidence yet."])
        lines.extend(items)
        lines.append("")

    lines.extend(
        [
            "## Related Work Draft",
            "",
            "This project surveys recent work related to the topic above. Existing papers generally emphasize stronger benchmark performance, clearer methodology, and better task alignment. Across the selected papers, a recurring pattern is the trade-off between effectiveness, robustness, and evaluation breadth.",
            "",
            "The current evidence suggests that the field is moving toward more modular pipelines, stronger evaluation discipline, and broader applicability across datasets. A useful next step is to compare methodological assumptions and identify which limitations remain unresolved.",
            "",
            "## Next Steps",
            "",
            "- Add more papers to improve coverage.",
            "- Refine evidence cards manually where needed.",
            "- Re-generate the note after adding new evidence.",
        ]
    )
    return "\n".join(lines)
