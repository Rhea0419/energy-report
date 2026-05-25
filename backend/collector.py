import requests
from datetime import datetime
from typing import Optional

from config import DAJIALA_KEY, DAJIALA_BASE, DAJIALA_ENDPOINT, ACCOUNTS
from models import Article, CollectionStatus, SystemState
from storage import (
    ensure_dirs, article_exists, save_article, load_state, save_state,
    count_articles,
)


class Collector:
    def __init__(self):
        ensure_dirs()
        self.state = load_state()
        self._init_accounts()

    def _init_accounts(self):
        for acct in ACCOUNTS:
            name = acct["name"]
            if name not in self.state.accounts:
                self.state.accounts[name] = CollectionStatus(
                    account_name=name,
                    biz=acct["biz"],
                )

    def _call_api(self, name: str = "", page: int = 1, biz: str = "", url: str = "") -> dict:
        payload = {
            "biz": biz, "url": url, "name": name,
            "page": page, "key": DAJIALA_KEY, "verifycode": "",
        }
        resp = requests.post(
            f"{DAJIALA_BASE}{DAJIALA_ENDPOINT}",
            json=payload, timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def collect_account(self, name: str, pages: int = 1) -> list[Article]:
        """Collect new articles from one account, up to `pages` pages."""
        cs = self.state.accounts.get(name)
        if not cs or not cs.enabled:
            return []

        raw = self._call_api(name=name, page=1)
        if raw.get("code") != 0:
            cs.error = raw.get("msg", "Unknown error")
            self._save()
            return []

        # Update account info from first-page response
        if raw.get("mp_nickname"):
            cs.biz = cs.biz or raw.get("mp_ghid", "")
        cs.total_pages = raw.get("total_page", 0)
        cs.error = ""

        # Update balance
        self.state.api_balance = raw.get("remain_money", self.state.api_balance)

        new_articles = []
        for page in range(1, pages + 1):
            if page > 1:
                raw = self._call_api(name=name, page=page)
                if raw.get("code") != 0:
                    break
                self.state.api_balance = raw.get("remain_money", self.state.api_balance)

            page_articles = 0
            for item in raw.get("data", []):
                appmsgid = item.get("appmsgid", 0)
                if article_exists(appmsgid):
                    continue  # dedup
                art = Article.from_api(item, source=name)
                save_article(art)
                new_articles.append(art)
                cs.last_appmsgid = max(cs.last_appmsgid, appmsgid)
                page_articles += 1

            cs.total_articles = count_articles(name)
            cs.last_page = page

            # If this page had no new articles, stop paginating
            if page_articles == 0:
                break

        cs.last_collected = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.state.total_articles_collected = count_articles()
        self._save()
        return new_articles

    def collect_all(self, pages_per_account: int = 1) -> dict[str, list[Article]]:
        """Collect from all enabled accounts."""
        results = {}
        for acct in ACCOUNTS:
            name = acct["name"]
            try:
                arts = self.collect_account(name, pages=pages_per_account)
                results[name] = arts
            except Exception as e:
                cs = self.state.accounts.get(name)
                if cs:
                    cs.error = str(e)
                results[name] = []
        self.state.last_global_collection = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._save()
        return results

    def get_status(self) -> dict:
        self.state.total_articles_collected = count_articles()
        return {
            "last_global_collection": self.state.last_global_collection,
            "total_articles_collected": self.state.total_articles_collected,
            "api_balance": self.state.api_balance,
            "accounts": [
                {
                    "name": cs.account_name,
                    "biz": cs.biz,
                    "total_articles": count_articles(cs.account_name),
                    "last_collected": cs.last_collected,
                    "enabled": cs.enabled,
                    "error": cs.error,
                }
                for cs in self.state.accounts.values()
            ],
        }

    def _save(self):
        save_state(self.state)


_collector_instance: Optional[Collector] = None


def get_collector() -> Collector:
    global _collector_instance
    if _collector_instance is None:
        _collector_instance = Collector()
    return _collector_instance
