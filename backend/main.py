from fastapi import FastAPI, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path

from collector import get_collector
from analyzer import get_analyzer
from storage import list_articles, count_articles, get_recent_months, save_knowledge_base
from reporter import generate_and_save, list_reports, get_report, get_available_months
from scheduler import get_scheduler_status


@asynccontextmanager
async def lifespan(app: FastAPI):
    from storage import ensure_dirs
    ensure_dirs()
    from scheduler import start_scheduler, stop_scheduler
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="能源行业月报系统", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 采集 API ──────────────────────────────────────

@app.get("/api/status")
def get_status():
    return get_collector().get_status()


@app.post("/api/collect")
def trigger_collection(
    account: str = "",
    pages: int = Query(default=1, ge=1, le=5),
):
    collector = get_collector()
    if account:
        articles = collector.collect_account(account, pages=pages)
        return {"account": account, "new_articles": len(articles), "articles": [
            {"title": a.title, "url": a.url, "post_time": a.post_time_str} for a in articles
        ]}
    else:
        results = collector.collect_all(pages_per_account=pages)
        total = sum(len(v) for v in results.values())
        return {"total_new": total, "accounts": {
            k: len(v) for k, v in results.items()
        }}


# ── 文章 API ──────────────────────────────────────

@app.get("/api/articles")
def get_articles(
    source: str = "",
    month: str = "",
    category: str = "",
    keyword: str = "",
    analyzed_only: bool = False,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
):
    articles = list_articles(source=source, month=month, analyzed_only=analyzed_only, limit=limit, offset=offset)

    # Post-filter by category and keyword
    if category:
        articles = [a for a in articles if category in a.category]
    if keyword:
        kw = keyword.lower()
        articles = [a for a in articles if kw in a.title.lower() or kw in a.ai_summary.lower()]

    return {
        "total": len(articles),
        "articles": [
            {
                "appmsgid": a.appmsgid,
                "title": a.title,
                "source": a.source,
                "url": a.url,
                "post_time": a.post_time_str,
                "digest": a.digest,
                "cover_url": a.cover_url,
                "category": a.category,
                "ai_tags": a.ai_tags,
                "ai_summary": a.ai_summary,
                "ai_key_data": a.ai_key_data,
                "ai_policy": a.ai_policy,
                "ai_viewpoint": a.ai_viewpoint,
                "importance": a.importance,
                "ai_analyzed": a.ai_analyzed,
            }
            for a in articles
        ],
    }


@app.get("/api/articles/stats")
def get_article_stats():
    sources = {}
    total = 0
    for a in list_articles(limit=10000):
        total += 1
        sources[a.source] = sources.get(a.source, 0) + 1

    return {
        "total": total,
        "by_source": sources,
        "by_category": {},  # computed from frontmatter aggregation
        "months": get_recent_months(12),
    }


# ── AI 分析 API ───────────────────────────────────

@app.post("/api/analyze")
def trigger_analysis(limit: int = Query(default=10, le=50)):
    analyzer = get_analyzer()
    results = analyzer.analyze_unanalyzed(limit=limit)
    return {
        "analyzed": len(results),
        "articles": [
            {"title": a.title, "source": a.source, "ai_summary": a.ai_summary,
             "importance": a.importance}
            for a in results
        ],
    }


@app.post("/api/knowledge-base/update")
def update_knowledge_base(month: str = ""):
    if not month:
        from datetime import datetime
        month = datetime.now().strftime("%Y-%m")
    save_knowledge_base(month)
    return {"status": "ok", "month": month}


# ── 月报 API ──────────────────────────────────────

@app.get("/api/reports")
def get_reports():
    return {"reports": list_reports(), "months": get_available_months()}


@app.post("/api/reports/generate")
def generate_report(month: str = "", theme: str = "综合"):
    result = generate_and_save(month=month, theme=theme)
    return result


@app.get("/api/reports/{month}/{theme}")
def read_report(month: str, theme: str):
    report = get_report(month, theme)
    if report is None:
        return {"error": "Report not found"}, 404
    return report


# ── 知识库 API ────────────────────────────────────

@app.get("/api/knowledge-base")
def get_knowledge_base(month: str = "", category: str = ""):
    articles = list_articles(month=month, analyzed_only=True)
    if category:
        articles = [a for a in articles if category in a.category]

    data_points = []
    policies = []
    viewpoints = []

    for a in articles:
        if a.ai_key_data:
            data_points.extend(a.ai_key_data)
        if a.ai_policy:
            policies.extend(a.ai_policy)
        if a.ai_viewpoint:
            viewpoints.append({
                "title": a.title, "source": a.source,
                "viewpoint": a.ai_viewpoint, "date": a.post_time_str,
            })

    return {
        "month": month,
        "article_count": len(articles),
        "data_points": data_points,
        "policies": policies,
        "viewpoints": viewpoints,
        "categories": list(set(
            cat for a in articles for cat in a.category
        )),
    }


# ── 往期报告 API ────────────────────────────────

@app.get("/api/past-reports")
def get_past_reports():
    from pdf_extractor import get_report_list
    return {"reports": get_report_list()}


@app.get("/api/past-reports/{filename}")
def get_past_report(filename: str):
    from pdf_extractor import get_report_content
    report = get_report_content(filename)
    if report is None:
        return {"error": "Report not found"}, 404
    return report


# ── 调度器 API ───────────────────────────────────

@app.get("/api/scheduler")
def scheduler_status():
    return get_scheduler_status()


# ── 前端页面 ──────────────────────────────────────

from fastapi.responses import FileResponse

FRONTEND_HTML = Path(__file__).parent.parent / "frontend" / "index.html"


@app.get("/")
def serve_frontend():
    if FRONTEND_HTML.exists():
        return FileResponse(str(FRONTEND_HTML), media_type="text/html")
    return {"message": "能源月报系统 API", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
