from __future__ import annotations

import json

from app.database import get_connection
from app.schemas import ResearchRequest, ResearchResponse


class ResearchRepository:
    def save(self, research: ResearchResponse, request: ResearchRequest) -> None:
        result_json = research.model_dump_json()
        request_json = request.model_dump_json()

        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO researches (
                    id,
                    query,
                    language,
                    status,
                    request_json,
                    result_json,
                    markdown_report,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    research.id,
                    research.query,
                    research.language,
                    research.status,
                    request_json,
                    result_json,
                    research.markdown_report,
                    research.created_at.isoformat(),
                ),
            )

            for source in research.sources:
                connection.execute(
                    """
                    INSERT INTO sources (
                        id,
                        research_id,
                        url,
                        title,
                        status_code,
                        content_type,
                        fetched_at,
                        extraction_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"{research.id}:{source.url}",
                        research.id,
                        source.url,
                        source.title,
                        source.status_code,
                        None,
                        source.fetched_at.isoformat() if source.fetched_at else research.created_at.isoformat(),
                        source.model_dump_json(),
                    ),
                )

    def get(self, research_id: str) -> ResearchResponse | None:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT result_json FROM researches WHERE id = ?",
                (research_id,),
            ).fetchone()

        if row is None:
            return None

        data = json.loads(row["result_json"])
        return ResearchResponse.model_validate(data)

    def get_report(self, research_id: str) -> str | None:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT markdown_report FROM researches WHERE id = ?",
                (research_id,),
            ).fetchone()

        if row is None:
            return None

        return str(row["markdown_report"])
