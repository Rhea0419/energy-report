import json
import requests
from pathlib import Path
from typing import Optional

from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, OPENROUTER_BASE, CATEGORIES
from models import Article
from storage import (
    list_articles, read_frontmatter, update_article_frontmatter,
    RAW_ARTICLE_DIR, save_knowledge_base,
)

ANALYSIS_PROMPT = """你是一位采购研究中心资深分析师。分析以下文章，提取关键信息，以JSON格式返回（只返回JSON，不要其他文字）。

文章标题：{title}
文章摘要：{digest}

请提取：
1. category: 从以下分类中选择1-3个最相关的：{categories}
2. tags: 3-5个关键词标签
3. summary: 一句话概括核心内容（50字以内）
4. key_data: 文章中提到的结构化数据，格式 [{{"指标":"名称","数值":"值","单位":"单位"}}]。如果文章没有具体数据则返回空数组
5. policy: 涉及的政策法规，格式 [{{"名称":"政策名","发布机构":"机构名","要点":"核心要点"}}]。没有则返回空数组
6. viewpoint: 文章核心观点或行业判断（100字以内）。纯新闻稿可留空字符串
7. importance: 重要程度1-5（1=一般资讯，3=行业重要动态，5=重大政策/行业转折点）

返回格式：
{{"category":[],"tags":[],"summary":"","key_data":[],"policy":[],"viewpoint":"","importance":1}}"""

REPORT_PROMPT = """你是一位采购研究中心资深分析师，为"供应链服务中心（采购研究中心）"撰写月度报告。

报告主题：{theme}
报告月份：{month}

【往期报告风格参考】
{style_reference}

【本月素材】
{articles_text}

请模仿往期报告的专业风格，按以下结构撰写月报。要求：数据准确、分析深入、语言精练，政策解读要参考往期报告的专业表述方式。

## 一、本月概览
200字左右的月度综述，概括最重要的趋势和变化。

## 二、关键数据
用Markdown表格列出本月关键数据：
| 指标 | 数值 | 环比变化 | 来源 |
|------|------|----------|------|

## 三、政策法规
按重要性排列本月重要政策，每条包括名称、发布机构、要点和影响分析。政策解读参考往期报告的深度和格式。

## 四、行业要闻
按时间线排列重要事件（5-10条），每条100字左右。

## 五、重点企业动态
主要企业的重要动向。

## 六、趋势研判
200字左右的行业趋势分析和展望。参考往期"综合分析"栏目的写法。

直接输出Markdown格式的月报内容。"""


class Analyzer:
    def __init__(self):
        self.api_key = ANTHROPIC_API_KEY
        self.model = ANTHROPIC_MODEL
        self.base_url = OPENROUTER_BASE

    def _call_llm(self, prompt: str, max_tokens: int = 1024) -> str:
        """Call OpenRouter API (OpenAI-compatible format)."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120,
            proxies={"http": None, "https": None},
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def analyze_article(self, article: Article) -> Article:
        """Analyze a single article and enrich it with AI-extracted data."""
        if not self.api_key:
            return article

        prompt = ANALYSIS_PROMPT.format(
            title=article.title,
            digest=article.digest[:1000],
            categories="、".join(CATEGORIES),
        )

        try:
            text = self._call_llm(prompt, max_tokens=1024)
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            result = json.loads(text.strip())

            article.category = result.get("category", [])[:3]
            article.ai_tags = result.get("tags", [])[:5]
            article.ai_summary = result.get("summary", "")
            article.ai_key_data = result.get("key_data", [])
            article.ai_policy = result.get("policy", [])
            article.ai_viewpoint = result.get("viewpoint", "")
            article.importance = int(result.get("importance", 1))
            article.ai_analyzed = True
        except Exception as e:
            article.ai_summary = f"[分析失败: {e}]"
            article.ai_analyzed = False

        return article

    def analyze_unanalyzed(self, limit: int = 20) -> list[Article]:
        """Find and analyze articles that haven't been analyzed yet."""
        results = []
        count = 0
        for md in sorted(RAW_ARTICLE_DIR.rglob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
            if count >= limit:
                break
            fm = read_frontmatter(md)
            if not fm or fm.get("ai_summary"):
                continue

            art = Article(
                appmsgid=fm.get("appmsgid", 0),
                title=fm.get("title", ""),
                url=fm.get("url", ""),
                digest=fm.get("digest", ""),
                cover_url=fm.get("cover_url", ""),
                post_time=0,
                post_time_str=fm.get("post_time", ""),
                position=fm.get("position", 0),
                item_show_type=fm.get("item_show_type", 0),
                msg_status=0, msg_fail_reason="", is_deleted="0",
                original=0, types=0, pre_post_time=0, update_time=0,
                send_to_fans_num=-1, pic_cdn_url_16_9="",
                pic_cdn_url_1_1="", pic_cdn_url_235_1="",
                source=fm.get("source", ""),
            )

            art = self.analyze_article(art)
            if art.ai_analyzed:
                update_article_frontmatter(md, art)
                results.append(art)
                count += 1

        if results:
            months = set(a.month_key for a in results)
            for m in months:
                save_knowledge_base(m)

        return results

    def generate_report(self, month: str, theme: str = "综合") -> str:
        """Generate a monthly report for a given month and theme, referencing past reports."""
        if not self.api_key:
            return "# 错误: 未配置 AI API Key"

        articles = list_articles(month=month, analyzed_only=True)
        if theme != "综合":
            articles = [a for a in articles if theme in a.category]

        if not articles:
            return f"# {theme}月报 — {month}\n\n本月暂无相关文章数据。"

        articles_text = "\n\n---\n\n".join([
            f"### {a.title}\n来源: {a.source} | {a.post_time_str}\n摘要: {a.ai_summary}\n"
            f"数据: {json.dumps(a.ai_key_data, ensure_ascii=False)}\n"
            f"政策: {json.dumps(a.ai_policy, ensure_ascii=False)}\n"
            f"观点: {a.ai_viewpoint}"
            for a in articles[:50]
        ])

        # Build style reference from past reports
        style_ref = "暂无往期报告参考。"
        try:
            from pdf_extractor import build_report_context, search_past_reports
            style_ref = build_report_context(max_chars=3000)
            if not style_ref:
                style_ref = "暂无往期报告参考。"
        except Exception:
            pass

        prompt = REPORT_PROMPT.format(
            theme=theme, month=month,
            articles_text=articles_text,
            style_reference=style_ref,
        )

        try:
            return self._call_llm(prompt, max_tokens=4096)
        except Exception as e:
            return f"# 生成失败\n\n错误: {e}"


_analyzer_instance: Optional[Analyzer] = None


def get_analyzer() -> Analyzer:
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = Analyzer()
    return _analyzer_instance