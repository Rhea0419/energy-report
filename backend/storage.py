import json
import re
import yaml
from pathlib import Path
from datetime import datetime
from typing import Optional

from config import (
    RAW_ARTICLE_DIR, KNOWLEDGE_BASE_DIR, REPORTS_DIR,
    SYSTEM_DIR, STATE_FILE,
)
from models import Article, SystemState, CollectionStatus


def ensure_dirs():
    for d in [RAW_ARTICLE_DIR, KNOWLEDGE_BASE_DIR, REPORTS_DIR, SYSTEM_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    for sub in ["themes", "data-points", "policies", "viewpoints"]:
        (KNOWLEDGE_BASE_DIR / sub).mkdir(parents=True, exist_ok=True)


def sanitize_filename(title: str, max_len: int = 80) -> str:
    s = re.sub(r'[\\/:*?"<>|]', "-", title)
    return s[:max_len].rstrip()


def article_exists(appmsgid: int) -> bool:
    for md in RAW_ARTICLE_DIR.rglob("*.md"):
        try:
            front = read_frontmatter(md)
            if front and front.get("appmsgid") == appmsgid:
                return True
        except Exception:
            pass
    return False


def save_article(article: Article) -> Path:
    month = article.month_key
    target_dir = RAW_ARTICLE_DIR / article.source / month
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = sanitize_filename(article.title) + ".md"
    filepath = target_dir / filename

    frontmatter = {
        "appmsgid": article.appmsgid,
        "title": article.title,
        "source": article.source,
        "url": article.url,
        "post_time": article.post_time_str,
        "position": article.position,
        "item_show_type": article.item_show_type,
        "digest": article.digest,
        "cover_url": article.cover_url,
        "category": article.category,
        "ai_tags": article.ai_tags,
        "ai_summary": article.ai_summary,
        "ai_key_data": article.ai_key_data,
        "ai_policy": article.ai_policy,
        "ai_viewpoint": article.ai_viewpoint,
        "importance": article.importance,
    }

    content = f"---\n{yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False)}---\n\n"
    content += f"# {article.title}\n\n"
    content += f"> 原文链接: {article.url}\n\n"
    content += f"{article.digest}\n"

    filepath.write_text(content, encoding="utf-8")
    return filepath


def update_article_frontmatter(filepath: Path, article: Article):
    existing = filepath.read_text(encoding="utf-8")
    body = existing.split("---\n", 2)[-1] if existing.startswith("---") else existing

    frontmatter = {
        "appmsgid": article.appmsgid,
        "title": article.title,
        "source": article.source,
        "url": article.url,
        "post_time": article.post_time_str,
        "position": article.position,
        "item_show_type": article.item_show_type,
        "digest": article.digest,
        "cover_url": article.cover_url,
        "category": article.category,
        "ai_tags": article.ai_tags,
        "ai_summary": article.ai_summary,
        "ai_key_data": article.ai_key_data,
        "ai_policy": article.ai_policy,
        "ai_viewpoint": article.ai_viewpoint,
        "importance": article.importance,
    }

    new_content = f"---\n{yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False)}---\n{body}"
    filepath.write_text(new_content, encoding="utf-8")


def read_frontmatter(filepath: Path) -> Optional[dict]:
    text = filepath.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return None
    return yaml.safe_load(parts[1]) or {}


def load_state() -> SystemState:
    ensure_dirs()
    if STATE_FILE.exists():
        raw = json.loads(STATE_FILE.read_text())
        state = SystemState()
        state.last_global_collection = raw.get("last_global_collection", "")
        state.total_articles_collected = raw.get("total_articles_collected", 0)
        state.api_balance = raw.get("api_balance", 0.0)
        for name, s in raw.get("accounts", {}).items():
            cs = CollectionStatus(
                account_name=name,
                biz=s.get("biz", ""),
                total_articles=s.get("total_articles", 0),
                last_page=s.get("last_page", 0),
                total_pages=s.get("total_pages", 0),
                last_collected=s.get("last_collected", ""),
                last_appmsgid=s.get("last_appmsgid", 0),
                enabled=s.get("enabled", True),
                error=s.get("error", ""),
            )
            state.accounts[name] = cs
        return state
    return SystemState()


def save_state(state: SystemState):
    ensure_dirs()
    raw = {
        "last_global_collection": state.last_global_collection,
        "total_articles_collected": state.total_articles_collected,
        "api_balance": state.api_balance,
        "accounts": {},
    }
    for name, cs in state.accounts.items():
        raw["accounts"][name] = {
            "biz": cs.biz,
            "total_articles": cs.total_articles,
            "last_page": cs.last_page,
            "total_pages": cs.total_pages,
            "last_collected": cs.last_collected,
            "last_appmsgid": cs.last_appmsgid,
            "enabled": cs.enabled,
            "error": cs.error,
        }
    STATE_FILE.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")


def save_knowledge_base(month: str):
    articles = list_articles(month=month, analyzed_only=True)
    if not articles:
        return

    themes = {}
    data_points = []
    policies = []
    viewpoints = []

    for art in articles:
        for cat in art.category or ["其他"]:
            themes.setdefault(cat, []).append(art)
        if art.ai_key_data:
            data_points.extend(art.ai_key_data)
        if art.ai_policy:
            policies.extend(art.ai_policy)
        if art.ai_viewpoint:
            viewpoints.append({
                "title": art.title, "source": art.source,
                "viewpoint": art.ai_viewpoint, "date": art.post_time_str,
            })

    for cat, arts in themes.items():
        cat_file = KNOWLEDGE_BASE_DIR / "themes" / f"{cat}.md"
        arts_by_importance = sorted(arts, key=lambda a: a.importance, reverse=True)
        lines = [f"# {cat} — {month}", "", f"共 {len(arts)} 篇相关文章", ""]
        for i, art in enumerate(arts_by_importance, 1):
            stars = "⭐" * art.importance if art.importance else ""
            lines.append(f"## {i}. {art.title} {stars}")
            lines.append(f"- 来源: {art.source} | {art.post_time_str}")
            lines.append(f"- 链接: {art.url}")
            if art.ai_summary:
                lines.append(f"- 摘要: {art.ai_summary}")
            if art.ai_tags:
                lines.append(f"- 标签: {'、'.join(art.ai_tags)}")
            lines.append("")
        cat_file.write_text("\n".join(lines), encoding="utf-8")

    dp_dir = KNOWLEDGE_BASE_DIR / "data-points" / month
    dp_dir.mkdir(parents=True, exist_ok=True)
    lines = [f"# {month} 关键数据汇总", ""]
    if data_points:
        lines.append("| 指标 | 数值 | 单位 |")
        lines.append("|------|------|------|")
        for dp in data_points:
            name = dp.get("指标", dp.get("name", ""))
            value = dp.get("数值", dp.get("value", ""))
            unit = dp.get("单位", dp.get("unit", ""))
            lines.append(f"| {name} | {value} | {unit} |")
    else:
        lines.append("本月暂无数据。")
    (dp_dir / "数据汇总.md").write_text("\n".join(lines), encoding="utf-8")

    pol_dir = KNOWLEDGE_BASE_DIR / "policies" / month
    pol_dir.mkdir(parents=True, exist_ok=True)
    lines = [f"# {month} 政策动态", ""]
    if policies:
        for i, p in enumerate(policies, 1):
            name = p.get("名称", p.get("name", ""))
            org = p.get("发布机构", p.get("org", ""))
            points = p.get("要点", p.get("points", ""))
            lines.append(f"## {i}. {name}")
            if org:
                lines.append(f"- 发布机构: {org}")
            if points:
                lines.append(f"- 要点: {points}")
            lines.append("")
    else:
        lines.append("本月暂无重要政策。")
    (pol_dir / "政策动态.md").write_text("\n".join(lines), encoding="utf-8")

    vp_dir = KNOWLEDGE_BASE_DIR / "viewpoints" / month
    vp_dir.mkdir(parents=True, exist_ok=True)
    lines = [f"# {month} 行业观点摘编", ""]
    if viewpoints:
        for i, vp in enumerate(viewpoints, 1):
            lines.append(f"## {i}. {vp['title']}")
            lines.append(f"- 来源: {vp['source']} | {vp['date']}")
            lines.append(f"- 观点: {vp['viewpoint']}")
            lines.append("")
    else:
        lines.append("本月暂无观点摘编。")
    (vp_dir / "观点摘编.md").write_text("\n".join(lines), encoding="utf-8")


def list_articles(
    source: str = "",
    month: str = "",
    analyzed_only: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> list:
    results = []
    pattern = f"{source}/**/*.md" if source else "**/*.md"

    for md in RAW_ARTICLE_DIR.glob(pattern):
        fm = read_frontmatter(md)
        if not fm:
            continue
        if analyzed_only and not fm.get("ai_summary"):
            continue
        post_time = fm.get("post_time", "")
        if month and not post_time.startswith(month):
            continue

        art = Article(
            appmsgid=fm.get("appmsgid", 0),
            title=fm.get("title", ""),
            url=fm.get("url", ""),
            digest=fm.get("digest", ""),
            cover_url=fm.get("cover_url", ""),
            post_time=0,
            post_time_str=post_time,
            position=fm.get("position", 0),
            item_show_type=fm.get("item_show_type", 0),
            msg_status=0, msg_fail_reason="", is_deleted="0",
            original=0, types=0, pre_post_time=0, update_time=0,
            send_to_fans_num=-1,
            pic_cdn_url_16_9="", pic_cdn_url_1_1="", pic_cdn_url_235_1="",
            source=fm.get("source", source),
            category=fm.get("category", []),
            ai_tags=fm.get("ai_tags", []),
            ai_summary=fm.get("ai_summary", ""),
            ai_key_data=fm.get("ai_key_data", []),
            ai_policy=fm.get("ai_policy", []),
            ai_viewpoint=fm.get("ai_viewpoint", ""),
            importance=fm.get("importance", 0),
            ai_analyzed=bool(fm.get("ai_summary")),
        )
        results.append(art)

    results.sort(key=lambda a: a.post_time_str, reverse=True)
    return results[offset:offset + limit]


def count_articles(source: str = "") -> int:
    pattern = f"{source}/**/*.md" if source else "**/*.md"
    return sum(1 for _ in RAW_ARTICLE_DIR.glob(pattern))


def get_recent_months(n: int = 6) -> list:
    months = set()
    for md in RAW_ARTICLE_DIR.rglob("*.md"):
        fm = read_frontmatter(md)
        if fm and fm.get("post_time"):
            months.add(fm["post_time"][:7])
    return sorted(months, reverse=True)[:n]
