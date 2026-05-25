"""Extract past monthly reports from PDFs and build reference store."""
from __future__ import annotations
import os
import re
from pathlib import Path

# Use system Python 3.9 which has fitz installed
import subprocess
import json


PDF_DIR = Path("/Users/rhea/Obsidian data/work/采购研究月报")
OUTPUT_DIR = Path("/Users/rhea/Obsidian data/work/past-reports")
SYSTEM_PYTHON = "/Library/Developer/CommandLineTools/usr/bin/python3"


def extract_all_pdfs() -> list[dict]:
    """Extract text from all PDFs and save as Markdown."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    extract_script = """
import fitz, os, json, sys, re

pdf_dir = sys.argv[1]
output_dir = sys.argv[2]

results = []
for f in sorted(os.listdir(pdf_dir)):
    if not f.endswith('.pdf'):
        continue
    path = os.path.join(pdf_dir, f)
    doc = fitz.open(path)
    pages = doc.page_count

    full_text = ""
    for page_num in range(pages):
        full_text += doc[page_num].get_text()
    doc.close()

    # Parse sections based on the known structure
    sections = {}
    current_section = "前言"
    current_text = []

    section_markers = [
        "政策动态", "国际观察", "供应链动态", "技术视野",
        "采购动态", "产业链动态", "综合分析", "专项分析",
        "本期专题", "行业综述", "热点话题",
        "储能板块", "火电板块", "光伏板块", "风电板块",
    ]

    for line in full_text.split('\\n'):
        line_stripped = line.strip()
        if line_stripped in section_markers:
            if current_text:
                sections[current_section] = '\\n'.join(current_text)
            current_section = line_stripped
            current_text = []
        else:
            current_text.append(line)

    if current_text:
        sections[current_section] = '\\n'.join(current_text)

    # Extract title from filename
    title = f.replace('.pdf', '')

    # Extract key info
    issue_match = re.search(r'第(\\d+)期', title)
    issue_num = issue_match.group(1) if issue_match else '?'
    year_match = re.search(r'(\\d{4})', title)
    year = year_match.group(1) if year_match else '2025'

    results.append({
        'filename': f,
        'title': title,
        'year': year,
        'issue': issue_num,
        'pages': pages,
        'sections': {k: v[:5000] for k, v in sections.items()},  # cap per section
        'full_text': full_text[:30000],
    })

    # Save as markdown
    md_filename = f'{title}.md'
    md_path = os.path.join(output_dir, md_filename)
    with open(md_path, 'w', encoding='utf-8') as out:
        out.write(f'# {title}\\n\\n')
        out.write(f'**期数**: 第{issue_num}期 | **年**: {year} | **页数**: {pages}\\n\\n')
        out.write(f'---\\n\\n')
        for section_name, content in sections.items():
            out.write(f'## {section_name}\\n\\n')
            out.write(content[:3000])
            out.write('\\n\\n---\\n\\n')

    print(f'Extracted: {md_filename}', file=sys.stderr)

print(json.dumps(results, ensure_ascii=False))
"""
    proc = subprocess.run(
        [SYSTEM_PYTHON, "-c", extract_script, str(PDF_DIR), str(OUTPUT_DIR)],
        capture_output=True, text=True, timeout=60,
    )
    print(proc.stderr)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        print("STDOUT:", proc.stdout[:500])
        return []


def search_past_reports(query: str, reports: list[dict] = None) -> list[dict]:
    """Simple keyword search across past reports."""
    if reports is None:
        reports = load_report_index()

    results = []
    keywords = query.lower().split()
    for r in reports:
        full = r.get("full_text", "").lower()
        score = sum(1 for kw in keywords if kw in full)
        if score > 0:
            # Extract matching sections
            matching_sections = []
            for section_name, content in r.get("sections", {}).items():
                if any(kw in content.lower() for kw in keywords):
                    matching_sections.append({
                        "section": section_name,
                        "content": content[:1000],
                    })
            results.append({
                "title": r["title"],
                "issue": r["issue"],
                "year": r["year"],
                "score": score,
                "matching_sections": matching_sections[:5],
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:5]


def build_report_context(reports: list[dict] = None, max_chars: int = 5000) -> str:
    """Build a condensed context string from past reports for use in AI prompts."""
    if reports is None:
        reports = load_report_index()

    context_parts = []
    total_chars = 0
    for r in sorted(reports, key=lambda x: x.get("issue", ""), reverse=True):
        # Extract key sections: 综合分析, 本期专题, 专项分析 first (most important)
        important_sections = []
        for key in ["综合分析", "专项分析", "本期专题", "行业综述"]:
            content = r.get("sections", {}).get(key, "")
            if content:
                important_sections.append(f"【{key}】{content[:800]}")

        if important_sections:
            part = f"## {r['title']}\n" + "\n".join(important_sections)
            if total_chars + len(part) <= max_chars:
                context_parts.append(part)
                total_chars += len(part)

    return "\n\n".join(context_parts)


def load_report_index() -> list[dict]:
    """Load report index from extracted markdown files."""
    results = []
    index_file = OUTPUT_DIR / "index.json"
    if index_file.exists():
        return json.loads(index_file.read_text())

    for md in sorted(OUTPUT_DIR.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        sections = {}
        current_section = ""
        current_content = []

        for line in text.split("\n"):
            if line.startswith("## ") and not line.startswith("## "):
                section_name = line[3:].strip()
                # Skip metadata sections
                if current_section:
                    sections[current_section] = "\n".join(current_content)
                current_section = section_name
                current_content = []
            elif current_section:
                current_content.append(line)

        if current_section and current_content:
            sections[current_section] = "\n".join(current_content)

        # Parse title for year/issue
        title = md.stem
        issue_match = re.search(r"第(\d+)期", title)
        year_match = re.search(r"(\d{4})", title)

        results.append({
            "title": title,
            "filename": md.name,
            "year": year_match.group(1) if year_match else "",
            "issue": issue_match.group(1) if issue_match else "",
            "sections": sections,
            "full_text": text[:30000],
        })

    index_file.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    return results


def get_report_list() -> list[dict]:
    """Get list of past reports for display."""
    reports = load_report_index()
    return [
        {
            "title": r["title"],
            "year": r["year"],
            "issue": r["issue"],
            "filename": r["filename"],
            "section_count": len(r.get("sections", {})),
        }
        for r in reports
    ]


def get_report_content(filename: str) -> dict | None:
    """Get full content of a specific past report."""
    md_path = OUTPUT_DIR / filename
    if not md_path.exists():
        return None

    text = md_path.read_text(encoding="utf-8")
    reports = load_report_index()
    for r in reports:
        if r["filename"] == filename:
            return {
                "title": r["title"],
                "year": r["year"],
                "issue": r["issue"],
                "content": text,
                "sections": r.get("sections", {}),
            }
    return None