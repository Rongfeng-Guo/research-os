from __future__ import annotations

from difflib import SequenceMatcher


def _split_blocks(text: str) -> list[str]:
    normalized = (text or "").strip()
    if not normalized:
        return []
    blocks = [block.strip() for block in normalized.split("\n\n")]
    return [block for block in blocks if block]


def build_diff_payload(before: str, after: str) -> dict:
    before_blocks = _split_blocks(before)
    after_blocks = _split_blocks(after)
    matcher = SequenceMatcher(a=before_blocks, b=after_blocks)
    blocks: list[dict] = []
    summary_counts = {"added": 0, "removed": 0, "unchanged": 0, "changed": 0}

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for block in before_blocks[i1:i2]:
                blocks.append({"kind": "unchanged", "before": block, "after": block})
                summary_counts["unchanged"] += 1
            continue
        if tag == "delete":
            for block in before_blocks[i1:i2]:
                blocks.append({"kind": "removed", "before": block, "after": ""})
                summary_counts["removed"] += 1
            continue
        if tag == "insert":
            for block in after_blocks[j1:j2]:
                blocks.append({"kind": "added", "before": "", "after": block})
                summary_counts["added"] += 1
            continue

        paired = max(i2 - i1, j2 - j1)
        for idx in range(paired):
            before_block = before_blocks[i1 + idx] if i1 + idx < i2 else ""
            after_block = after_blocks[j1 + idx] if j1 + idx < j2 else ""
            kind = "changed"
            if before_block and not after_block:
                kind = "removed"
            elif after_block and not before_block:
                kind = "added"
            blocks.append({"kind": kind, "before": before_block, "after": after_block})
            summary_counts[kind] += 1

    return {
        "blocks": blocks,
        "summary": summary_counts,
        "before_preview": "\n\n".join(before_blocks[:2]),
        "after_preview": "\n\n".join(after_blocks[:2]),
    }
