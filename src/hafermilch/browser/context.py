from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PageContext:
    """A snapshot of the browser state at a single point in time."""

    url: str
    title: str
    # Raw PNG bytes of the visible viewport (None when provider has no vision)
    screenshot: bytes | None
    # Flattened text representation of the accessibility tree
    accessibility_tree: str
    # Page dimensions
    viewport_width: int = 1280
    viewport_height: int = 800

    def to_llm_parts(self, include_screenshot: bool = True) -> list[dict]:
        """Convert to the multimodal content-parts format understood by providers."""
        parts: list[dict] = [
            {
                "type": "text",
                "text": (
                    f"URL: {self.url}\n"
                    f"Title: {self.title}\n\n"
                    f"Accessibility tree:\n{self.accessibility_tree}"
                ),
            }
        ]
        if include_screenshot and self.screenshot:
            parts.append({"type": "image", "data": self.screenshot})
        return parts
