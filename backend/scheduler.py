from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import json
from pathlib import Path
from typing import Optional

from config import SYSTEM_DIR
from collector import get_collector
from analyzer import get_analyzer
from storage import save_knowledge_base
from reporter import generate_and_save


SCHEDULER_CONFIG = SYSTEM_DIR / "scheduler_config.json"
_scheduler: Optional[BackgroundScheduler] = None


def get_default_config() -> dict:
    return {
        "enabled": True,
        "jobs": {
            "collect_articles": {"cron": "0 8,18 * * *", "description": "文章采集（每天8:00和18:00）"},
            "ai_analysis": {"cron": "30 8,18 * * *", "description": "AI分析新文章（采集后30分钟）"},
            "knowledge_base": {"cron": "0 20 * * *", "description": "知识库聚合更新（每天20:00）"},
            "balance_check": {"cron": "0 9 * * *", "description": "余额检查（每天9:00）"},
            "monthly_report": {"cron": "0 8 1 * *", "description": "月报预生成（每月1日）"},
        },
    }


def load_config() -> dict:
    if SCHEDULER_CONFIG.exists():
        return json.loads(SCHEDULER_CONFIG.read_text())
    cfg = get_default_config()
    SCHEDULER_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULER_CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))
    return cfg


def save_config(cfg: dict):
    SCHEDULER_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULER_CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))


def job_collect_articles():
    print(f"[Scheduler] 开始采集文章: {datetime.now()}")
    collector = get_collector()
    results = collector.collect_all(pages_per_account=1)
    total = sum(len(v) for v in results.values())
    print(f"[Scheduler] 采集完成: {total} 篇新文章")


def job_ai_analysis():
    print(f"[Scheduler] 开始AI分析: {datetime.now()}")
    analyzer = get_analyzer()
    results = analyzer.analyze_unanalyzed(limit=20)
    print(f"[Scheduler] AI分析完成: {len(results)} 篇已分析")


def job_knowledge_base():
    month = datetime.now().strftime("%Y-%m")
    print(f"[Scheduler] 更新知识库: {month}")
    save_knowledge_base(month)


def job_balance_check():
    collector = get_collector()
    status = collector.get_status()
    balance = status["api_balance"]
    print(f"[Scheduler] 余额检查: ¥{balance:.2f}")
    if balance < 1.0:
        print(f"[Scheduler] ⚠️ 余额不足！当前余额: ¥{balance:.2f}")


def job_monthly_report():
    last_month = (datetime.now().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    print(f"[Scheduler] 生成月报: {last_month}")
    for theme in ["综合", "储能", "光伏", "风电"]:
        try:
            result = generate_and_save(month=last_month, theme=theme)
            print(f"[Scheduler] 月报已保存: {result['filepath']}")
        except Exception as e:
            print(f"[Scheduler] 月报生成失败({theme}): {e}")


def start_scheduler():
    global _scheduler
    cfg = load_config()
    if not cfg.get("enabled", True):
        return

    _scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    jobs = cfg.get("jobs", {})

    job_map = {
        "collect_articles": job_collect_articles,
        "ai_analysis": job_ai_analysis,
        "knowledge_base": job_knowledge_base,
        "balance_check": job_balance_check,
        "monthly_report": job_monthly_report,
    }

    for job_name, job_func in job_map.items():
        job_cfg = jobs.get(job_name, {})
        cron_expr = job_cfg.get("cron", "")
        if cron_expr:
            parts = cron_expr.strip().split()
            if len(parts) == 5:
                _scheduler.add_job(
                    job_func,
                    CronTrigger(
                        minute=parts[0], hour=parts[1],
                        day=parts[2], month=parts[3],
                        day_of_week=parts[4],
                        timezone="Asia/Shanghai",
                    ),
                    id=job_name,
                    name=job_cfg.get("description", job_name),
                    replace_existing=True,
                )

    _scheduler.start()
    print(f"[Scheduler] 定时任务已启动 ({len(_scheduler.get_jobs())} 个任务)")


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def get_scheduler_status() -> dict:
    cfg = load_config()
    jobs_info = {}
    if _scheduler:
        for job in _scheduler.get_jobs():
            jobs_info[job.id] = {
                "name": job.name,
                "next_run": str(job.next_run_time) if job.next_run_time else None,
            }
    return {"enabled": cfg.get("enabled", True), "jobs": jobs_info}
