from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup
import trafilatura

from app.schemas import ExtractResponse, ExtractedContent, LinkItem, PageMetadata


class ExtractorService:
    def extract(
        self,
        html: str,
        url: str | None = None,
        include_text: bool = True,
        include_links: bool = True,
    ) -> ExtractResponse:
        soup = BeautifulSoup(html, "lxml")

        for element in soup(["script", "style", "noscript", "template"]):
            element.decompose()

        title = self._extract_title(soup)
        metadata = self._extract_metadata(soup)
        text = self._extract_text(html, soup) if include_text else None
        links = self._extract_links(soup, url) if include_links else []

        extraction = ExtractedContent(
            url=str(url) if url else None,
            title=title or metadata.title,
            text=text,
            word_count=len(text.split()) if text else 0,
            links=links,
            metadata=metadata,
        )
        return ExtractResponse(extraction=extraction)

    def _extract_title(self, soup: BeautifulSoup) -> str | None:
        if soup.title and soup.title.string:
            return self._clean_text(soup.title.string)

        heading = soup.find("h1")
        if heading:
            return self._clean_text(heading.get_text(" ", strip=True))

        return None

    def _extract_metadata(self, soup: BeautifulSoup) -> PageMetadata:
        html_tag = soup.find("html")
        canonical = soup.find("link", rel=lambda value: value and "canonical" in value)

        return PageMetadata(
            title=self._meta_content(soup, "og:title") or self._meta_name(soup, "title"),
            description=self._meta_content(soup, "og:description") or self._meta_name(soup, "description"),
            language=html_tag.get("lang") if html_tag else None,
            canonical_url=canonical.get("href") if canonical else None,
            author=self._meta_name(soup, "author"),
            published_time=self._meta_content(soup, "article:published_time"),
        )

    def _extract_text(self, html: str, soup: BeautifulSoup) -> str:
        extracted = trafilatura.extract(html, include_comments=False, include_tables=True)
        if extracted:
            return self._clean_text(extracted)

        body = soup.body or soup
        return self._clean_text(body.get_text(" ", strip=True))

    def _extract_links(self, soup: BeautifulSoup, base_url: str | None) -> list[LinkItem]:
        links: list[LinkItem] = []
        seen: set[str] = set()

        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href")
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue

            absolute_url = urljoin(str(base_url), href) if base_url else href
            if absolute_url in seen:
                continue

            seen.add(absolute_url)
            links.append(
                LinkItem(
                    text=self._clean_text(anchor.get_text(" ", strip=True))[:180],
                    url=absolute_url,
                )
            )

        return links[:200]

    def _meta_name(self, soup: BeautifulSoup, name: str) -> str | None:
        tag = soup.find("meta", attrs={"name": name})
        return tag.get("content") if tag else None

    def _meta_content(self, soup: BeautifulSoup, property_name: str) -> str | None:
        tag = soup.find("meta", attrs={"property": property_name})
        return tag.get("content") if tag else None

    def _clean_text(self, value: str) -> str:
        return " ".join(value.split())
