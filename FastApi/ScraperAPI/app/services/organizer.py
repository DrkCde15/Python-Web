from __future__ import annotations

from collections import Counter
import re

from app.schemas import ResearchInsight, SourceResult


class OrganizerService:
    """Organizador local baseado em regras simples."""

    def organize(
        self,
        query: str,
        language: str,
        focus: list[str],
        sources: list[SourceResult],
    ) -> tuple[str, list[ResearchInsight], dict[str, list[str]], str]:
        successful_sources = [source for source in sources if source.summary]

        if not successful_sources:
            summary = "Nao foi possivel extrair conteudo util das fontes informadas."
            return summary, [], {}, self._build_report(query, language, focus, summary, [], {}, sources)

        joined_text = " ".join(source.summary or "" for source in successful_sources)
        keywords = self._keywords(joined_text, query)
        summary = self._summary(query, successful_sources, keywords)
        topics = self._topics(focus, keywords, successful_sources)
        entities = self._entities(joined_text)
        report = self._build_report(query, language, focus, summary, topics, entities, sources)

        return summary, topics, entities, report

    def summarize_source(self, text: str | None, limit_sentences: int = 3) -> tuple[str, list[str]]:
        if not text:
            return "", []

        sentences = self._sentences(text)
        selected = sentences[:limit_sentences]
        summary = " ".join(selected)
        key_points = selected[:5]
        return summary, key_points

    def _summary(self, query: str, sources: list[SourceResult], keywords: list[str]) -> str:
        source_count = len(sources)
        keyword_text = ", ".join(keywords[:6])
        return (
            f"A pesquisa sobre '{query}' analisou {source_count} fonte(s). "
            f"Os termos mais recorrentes foram: {keyword_text}. "
            "Consulte as fontes para validar os detalhes e aprofundar os pontos principais."
        )

    def _topics(
        self,
        focus: list[str],
        keywords: list[str],
        sources: list[SourceResult],
    ) -> list[ResearchInsight]:
        topics: list[ResearchInsight] = []

        for item in focus[:5]:
            notes = [
                source.summary
                for source in sources
                if source.summary and item.lower() in source.summary.lower()
            ][:3]
            if not notes:
                notes = [f"Use este foco para revisar as fontes relacionadas a {item}."]
            topics.append(ResearchInsight(name=item, notes=notes))

        if not topics:
            for keyword in keywords[:5]:
                notes = [
                    point
                    for source in sources
                    for point in source.key_points
                    if keyword.lower() in point.lower()
                ][:3]
                topics.append(
                    ResearchInsight(
                        name=keyword.title(),
                        notes=notes or [f"Termo recorrente nas fontes analisadas: {keyword}."],
                    )
                )

        return topics

    def _keywords(self, text: str, query: str) -> list[str]:
        stopwords = {
            "para",
            "com",
            "uma",
            "que",
            "dos",
            "das",
            "the",
            "and",
            "or",
            "in",
            "of",
            "to",
            "a",
            "e",
            "o",
            "as",
            "os",
            "de",
            "do",
            "da",
            "em",
            "no",
            "na",
        }
        words = re.findall(r"[A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9_-]{2,}", f"{query} {text}".lower())
        counter = Counter(word for word in words if word not in stopwords)
        return [word for word, _ in counter.most_common(12)]

    def _entities(self, text: str) -> dict[str, list[str]]:
        dates = sorted(set(re.findall(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b|\b\d{4}\b", text)))[:20]
        money = sorted(set(re.findall(r"(?:R\$|\$|€)\s?\d+(?:[.,]\d+)?", text)))[:20]
        names = sorted(set(re.findall(r"\b[A-ZÀ-Ý][A-Za-zÀ-ÿ]+(?:\s+[A-ZÀ-Ý][A-Za-zÀ-ÿ]+){0,3}\b", text)))[:30]

        return {
            "dates": dates,
            "money": money,
            "names": names,
        }

    def _sentences(self, text: str) -> list[str]:
        compact = " ".join(text.split())
        sentences = re.split(r"(?<=[.!?])\s+", compact)
        return [sentence.strip() for sentence in sentences if len(sentence.strip()) > 40][:12]

    def _build_report(
        self,
        query: str,
        language: str,
        focus: list[str],
        summary: str,
        topics: list[ResearchInsight],
        entities: dict[str, list[str]],
        sources: list[SourceResult],
    ) -> str:
        lines = [
            f"# Pesquisa: {query}",
            "",
            f"Idioma: {language}",
            "",
            "## Resumo",
            "",
            summary,
            "",
        ]

        if focus:
            lines.extend(["## Focos", "", *[f"- {item}" for item in focus], ""])

        if topics:
            lines.extend(["## Topicos", ""])
            for topic in topics:
                lines.append(f"### {topic.name}")
                lines.extend(f"- {note}" for note in topic.notes)
                lines.append("")

        if any(entities.values()):
            lines.extend(["## Entidades Detectadas", ""])
            for key, values in entities.items():
                if values:
                    lines.append(f"- {key}: {', '.join(values[:12])}")
            lines.append("")

        lines.extend(["## Fontes", ""])
        for source in sources:
            status = source.status_code if source.status_code is not None else "erro"
            title = source.title or source.url
            lines.append(f"- [{title}]({source.url}) - status: {status}")
            if source.error:
                lines.append(f"  - erro: {source.error}")
        lines.append("")

        return "\n".join(lines)
