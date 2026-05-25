from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from analyzer import get_analyzer
from storage import REPORTS_DIR, list_articles, get_recent_months


def generate_and_save(month: str = "", theme: str = "综合") -> dict:
    """Generate a report and save to Obsidian vault."""
    if not month:
        month = datetime.now().strftime("%Y-%m")

    analyzer = get_analyzer()
    content = analyzer.generate_report(month, theme)

    report_dir = REPORTS_DIR / month
    report_dir.mkdir(parents=True, exist_ok=True)
    filename = f"月报-{theme}.md"
    filepath = report_dir / filename
    filepath.write_text(content, encoding="utf-8")

    return {
        "month": month,
        "theme": theme,
        "filepath": str(filepath),
        "content": content,
    }


def list_reports() -> list[dict]:
    reports = []
    for md in sorted(REPORTS_DIR.rglob("*.md"), reverse=True):
        month = md.parent.name
        theme = md.stem.replace("月报-", "")
        reports.append({
            "month": month,
            "theme": theme,
            "filepath": str(md),
        })
    return reports


def get_report(month: str, theme: str) -> dict | None:
    filepath = REPORTS_DIR / month / f"月报-{theme}.md"
    if not filepath.exists():
        return None
    return {
        "month": month,
        "theme": theme,
        "filepath": str(filepath),
        "content": filepath.read_text(encoding="utf-8"),
    }


def get_available_months() -> list[str]:
    return get_recent_months(12)
