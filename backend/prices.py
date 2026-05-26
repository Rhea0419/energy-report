"""SMM price data access layer."""
import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "..", "Documents", "Kapathy", "commodities", "data", "prices.db"
)

# On cloud, use relative path
if os.getenv("HF_SPACE") or os.getenv("RENDER"):
    DB_PATH = "./data/prices.db"


def get_price_data(product: str = "", days: int = 30):
    """Get price time series for charts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    if product:
        rows = conn.execute(
            "SELECT date, name, low, high, avg, change_val, unit FROM prices "
            "WHERE name = ? AND date >= ? ORDER BY date",
            (product, date_from)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT date, name, low, high, avg, change_val, unit FROM prices "
            "WHERE date >= ? ORDER BY date, name",
            (date_from,)
        ).fetchall()
    
    conn.close()
    
    products = ["1#银", "SMM 1#电解铜", "SMM A00铝", "N型致密料", "SMM电池级碳酸锂指数"]
    result = {}
    for r in rows:
        name = r["name"]
        if name not in result:
            result[name] = {"name": name, "unit": r["unit"], "dates": [], "avgs": [], "highs": [], "lows": [], "changes": []}
        result[name]["dates"].append(r["date"])
        result[name]["avgs"].append(r["avg"])
        result[name]["highs"].append(r["high"])
        result[name]["lows"].append(r["low"])
        result[name]["changes"].append(r["change_val"])
    
    return {
        "products": [result[p] for p in products if p in result],
        "date_range": {"from": date_from, "to": datetime.now().strftime("%Y-%m-%d")}
    }


def get_latest_prices():
    """Get latest price snapshot."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    rows = conn.execute("""
        SELECT name, unit, avg, change_val, date FROM prices 
        WHERE (name, date) IN (
            SELECT name, MAX(date) FROM prices GROUP BY name
        )
    """).fetchall()
    
    conn.close()
    
    return [
        {"name": r["name"], "unit": r["unit"], "price": r["avg"], 
         "change": r["change_val"], "date": r["date"]}
        for r in rows
    ]
