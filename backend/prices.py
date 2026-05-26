"""SMM price data access layer."""
import sqlite3
import os
from datetime import datetime, timedelta

# Local: use the actual path. Cloud: use ../data/ (relative to backend/)
if os.getenv("HF_SPACE") or os.getenv("RENDER"):
    DB_PATH = "../data/prices.db"
else:
    DB_PATH = "/Users/rhea/Documents/Kapathy/commodities/data/prices.db"


def get_price_data(product: str = "", days: int = 30):
    """Get price time series for charts.
    Table columns: 0=id, 1=date, 2=name, 3=code, 4=category, 5=unit, 6=low, 7=high, 8=avg, 9=change
    """
    conn = sqlite3.connect(DB_PATH)
    
    date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    if product:
        rows = conn.execute(
            "SELECT * FROM prices WHERE \"2\" = ? AND \"1\" >= ? ORDER BY \"1\"",
            (product, date_from)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM prices WHERE \"1\" >= ? ORDER BY \"1\", \"2\"",
            (date_from,)
        ).fetchall()
    
    conn.close()
    
    products = ["1#银", "SMM 1#电解铜", "SMM A00铝", "N型致密料", "SMM电池级碳酸锂指数"]
    result = {}
    for r in rows:
        name = r[2]  # column 2 = product name
        if name not in result:
            result[name] = {"name": name, "unit": r[5], "dates": [], "avgs": [], "highs": [], "lows": [], "changes": []}
        result[name]["dates"].append(r[1])
        result[name]["avgs"].append(r[8])
        result[name]["highs"].append(r[7])
        result[name]["lows"].append(r[6])
        result[name]["changes"].append(r[9])
    
    return {
        "products": [result[p] for p in products if p in result],
        "date_range": {"from": date_from, "to": datetime.now().strftime("%Y-%m-%d")}
    }


def get_latest_prices():
    """Get latest price snapshot."""
    conn = sqlite3.connect(DB_PATH)
    
    rows = conn.execute("""
        SELECT * FROM prices 
        WHERE (\"2\", \"1\") IN (
            SELECT \"2\", MAX(\"1\") FROM prices GROUP BY \"2\"
        )
    """).fetchall()
    
    conn.close()
    
    return [
        {"name": r[2], "unit": r[5], "price": r[8], 
         "change": r[9], "date": r[1]}
        for r in rows
    ]
