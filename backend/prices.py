"""SMM price data access layer."""
import sqlite3
import os
from datetime import datetime, timedelta

if os.getenv("HF_SPACE") or os.getenv("RENDER"):
    DB_PATH = "../seed-data/prices.db"
else:
    DB_PATH = "/Users/rhea/Documents/Kapathy/commodities/data/prices.db"


PRODUCTS = ["1#银", "SMM 1#电解铜", "SMM A00铝", "N型致密料", "SMM电池级碳酸锂指数",
            "集中式PCS (1725kW)", "集中式PCS (2500kW)",
            "方形磷酸铁锂电池 (314Ah)", "方形磷酸铁锂电池 (280Ah)"]


def get_price_data(product: str = "", days: int = 180, date_from: str = "", date_to: str = ""):
    """Get price time series for charts."""
    conn = sqlite3.connect(DB_PATH)

    if date_from:
        start = date_from
    else:
        start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    end = date_to or datetime.now().strftime("%Y-%m-%d")

    if product:
        rows = conn.execute(
            "SELECT date, product_name, low, high, avg, change_val, unit FROM prices "
            "WHERE product_name = ? AND date >= ? AND date <= ? ORDER BY date",
            (product, start, end)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT date, product_name, low, high, avg, change_val, unit FROM prices "
            "WHERE date >= ? AND date <= ? ORDER BY date, product_name",
            (start, end)
        ).fetchall()
    conn.close()

    result = {}
    for r in rows:
        name = r[1]
        if name not in result:
            result[name] = {"name": name, "unit": r[6], "dates": [], "avgs": [],
                          "highs": [], "lows": [], "changes": []}
        result[name]["dates"].append(r[0])
        result[name]["avgs"].append(r[4])
        result[name]["highs"].append(r[3])
        result[name]["lows"].append(r[2])
        result[name]["changes"].append(r[5])

    return {
        "products": [result[p] for p in PRODUCTS if p in result],
        "date_range": {"from": start, "to": end}
    }


def get_latest_prices():
    """Get latest price per product."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT product_name, unit, avg, change_val, date FROM prices
        WHERE (product_name, date) IN (
            SELECT product_name, MAX(date) FROM prices GROUP BY product_name
        )
    """).fetchall()
    conn.close()

    return [
        {"name": r[0], "unit": r[1], "price": r[2], "change": r[3], "date": r[4]}
        for r in rows
    ]
