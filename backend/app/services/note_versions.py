from __future__ import annotations

import json

from sqlmodel import Session, select

from ..models import TopicNote, TopicNoteVersion


def create_note_version(
    session: Session,
    *,
    note: TopicNote,
    update_run_id: int | None = None,
    version_kind: str = "snapshot",
    source_suggestion_ids: list[int] | None = None,
) -> TopicNoteVersion:
    latest = session.exec(
        select(TopicNoteVersion)
        .where(TopicNoteVersion.note_id == note.id)
        .order_by(TopicNoteVersion.version_number.desc())
    ).first()
    version_number = 1 if not latest else latest.version_number + 1
    version = TopicNoteVersion(
        note_id=note.id,
        project_id=note.project_id,
        version_number=version_number,
        markdown=note.markdown,
        metadata_json=note.metadata_json or "{}",
        version_kind=version_kind,
        source_suggestion_ids_json=json.dumps(source_suggestion_ids or []),
        update_run_id=update_run_id,
    )
    session.add(version)
    session.commit()
    session.refresh(version)
    return version


def version_to_read(version: TopicNoteVersion) -> dict:
    return {
        "id": version.id,
        "note_id": version.note_id,
        "project_id": version.project_id,
        "version_number": version.version_number,
        "markdown": version.markdown,
        "metadata": json.loads(version.metadata_json or "{}"),
        "version_kind": version.version_kind or "snapshot",
        "source_suggestion_ids": json.loads(version.source_suggestion_ids_json or "[]"),
        "update_run_id": version.update_run_id,
        "created_at": version.created_at,
    }
