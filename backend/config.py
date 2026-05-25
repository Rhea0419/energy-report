import os
from pathlib import Path

DAJIALA_KEY = os.getenv("DAJIALA_KEY", "")
DAJIALA_BASE = "https://www.dajiala.com"
DAJIALA_ENDPOINT = "/fbmain/monitor/v3/post_history"

# Local development overrides (gitignored)
try:
    from local_config import DAJIALA_KEY as LOCAL_DAJIALA_KEY
    if not DAJIALA_KEY and LOCAL_DAJIALA_KEY:
        DAJIALA_KEY = LOCAL_DAJIALA_KEY
except ImportError:
    pass

# On Railway/cloud: use local data dir; on macOS: use Obsidian vault
_default_vault = "/Users/rhea/Obsidian data/work"
if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RENDER") or os.getenv("HF_SPACE"):
    _default_vault = "./data"
OBSIDIAN_VAULT = Path(os.getenv("OBSIDIAN_VAULT", _default_vault))

RAW_ARTICLE_DIR = OBSIDIAN_VAULT / "raw-article"
KNOWLEDGE_BASE_DIR = OBSIDIAN_VAULT / "knowledge-base"
REPORTS_DIR = OBSIDIAN_VAULT / "monthly-reports"
SYSTEM_DIR = OBSIDIAN_VAULT / "system"
STATE_FILE = SYSTEM_DIR / "collection_state.json"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY") or ""

# Local development overrides (gitignored)
try:
    from local_config import ANTHROPIC_API_KEY as LOCAL_ANTHROPIC_KEY
    if not ANTHROPIC_API_KEY and LOCAL_ANTHROPIC_KEY:
        ANTHROPIC_API_KEY = LOCAL_ANTHROPIC_KEY
except ImportError:
    pass
ANTHROPIC_MODEL = "anthropic/claude-4.6-sonnet-20260217"
OPENROUTER_BASE = "https://openrouter.ai/api/v1"

ACCOUNTS: list[dict[str, str]] = [
    {"name": "北极星储能网", "biz": ""},
    {"name": "北极星电力网", "biz": ""},
    {"name": "北极星风力发电网", "biz": ""},
    {"name": "北极星光伏学社", "biz": ""},
    {"name": "北极星火力发电网", "biz": ""},
    {"name": "北极星太阳能光伏网", "biz": ""},
    {"name": "CCPA风电混塔分会", "biz": ""},
    {"name": "储能领跑者联盟", "biz": ""},
    {"name": "储能头条", "biz": "gh_a5171980d152"},
    {"name": "风电头条", "biz": ""},
    {"name": "光伏头条", "biz": ""},
    {"name": "光伏們", "biz": ""},
    {"name": "海上风电", "biz": ""},
    {"name": "黑鹰光伏", "biz": ""},
    {"name": "索比光伏网", "biz": ""},
    {"name": "索比咨询", "biz": ""},
    {"name": "线缆哥", "biz": ""},
    {"name": "中国电力报", "biz": ""},
    {"name": "中国招标投标协会", "biz": ""},
]

CATEGORIES = ["储能", "光伏", "风电", "电力", "火电", "政策", "招中标", "企业动态", "技术进展", "其他"]
