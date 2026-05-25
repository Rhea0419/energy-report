from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Article:
    appmsgid: int
    title: str
    url: str
    digest: str
    cover_url: str
    post_time: int
    post_time_str: str
    position: int
    item_show_type: int
    msg_status: int
    msg_fail_reason: str
    is_deleted: str
    original: int
    types: int
    pre_post_time: int
    update_time: int
    send_to_fans_num: int
    pic_cdn_url_16_9: str
    pic_cdn_url_1_1: str
    pic_cdn_url_235_1: str

    # AI-enriched fields (populated later)
    source: str = ""
    category: list[str] = field(default_factory=list)
    ai_tags: list[str] = field(default_factory=list)
    ai_summary: str = ""
    ai_key_data: list[dict] = field(default_factory=list)
    ai_policy: list[dict] = field(default_factory=list)
    ai_viewpoint: str = ""
    importance: int = 0
    ai_analyzed: bool = False

    @classmethod
    def from_api(cls, raw: dict, source: str = "") -> "Article":
        return cls(
            appmsgid=raw.get("appmsgid", 0),
            title=raw.get("title", ""),
            url=raw.get("url", ""),
            digest=raw.get("digest", ""),
            cover_url=raw.get("cover_url", ""),
            post_time=raw.get("post_time", 0),
            post_time_str=raw.get("post_time_str", ""),
            position=raw.get("position", 0),
            item_show_type=raw.get("item_show_type", 0),
            msg_status=raw.get("msg_status", 0),
            msg_fail_reason=raw.get("msg_fail_reason", ""),
            is_deleted=raw.get("is_deleted", "0"),
            original=raw.get("original", 0),
            types=raw.get("types", 0),
            pre_post_time=raw.get("pre_post_time", 0),
            update_time=raw.get("update_time", 0),
            send_to_fans_num=raw.get("send_to_fans_num", -1),
            pic_cdn_url_16_9=raw.get("pic_cdn_url_16_9", ""),
            pic_cdn_url_1_1=raw.get("pic_cdn_url_1_1", ""),
            pic_cdn_url_235_1=raw.get("pic_cdn_url_235_1", ""),
            source=source,
        )

    @property
    def post_datetime(self) -> datetime:
        if self.post_time and self.post_time > 1000000000:
            return datetime.fromtimestamp(self.post_time)
        # Parse from post_time_str e.g. "2026-05-24 16:05:16"
        try:
            return datetime.strptime(self.post_time_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return datetime.fromtimestamp(0)

    @property
    def month_key(self) -> str:
        return self.post_datetime.strftime("%Y-%m")


@dataclass
class CollectionStatus:
    account_name: str
    biz: str
    total_articles: int = 0
    last_page: int = 0
    total_pages: int = 0
    last_collected: str = ""
    last_appmsgid: int = 0
    enabled: bool = True
    error: str = ""


@dataclass
class SystemState:
    accounts: dict[str, CollectionStatus] = field(default_factory=dict)
    last_global_collection: str = ""
    total_articles_collected: int = 0
    api_balance: float = 0.0
