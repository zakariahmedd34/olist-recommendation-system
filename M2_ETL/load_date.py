"""Step 4 — Populate Dim_Date for 2016-01-01 .. 2018-12-31 with holiday/season/payday cols."""
import pandas as pd
import holidays
from sqlalchemy import text
from db import engine

START, END = "2016-01-01", "2018-12-31"


def season_for(month: int) -> str:
    """Southern-hemisphere seasons (Brazil)."""
    if month in (12, 1, 2):
        return "Verão"
    if month in (3, 4, 5):
        return "Outono"
    if month in (6, 7, 8):
        return "Inverno"
    return "Primavera"


def main() -> None:
    br = holidays.Brazil()
    dates = pd.date_range(START, END, freq="D")

    df = pd.DataFrame({"date": dates.date})
    df["day"]          = dates.day
    df["monthnumber"]  = dates.month
    df["monthname"]    = dates.strftime("%B")
    df["quarter"]      = dates.quarter
    df["weekday"]      = dates.strftime("%A")
    df["year"]         = dates.year
    df["is_holiday"]   = [d in br for d in dates.date]
    df["holiday_name"] = [br.get(d) for d in dates.date]
    df["is_weekend"]   = dates.weekday >= 5
    df["season"]       = df["monthnumber"].map(season_for)
    df["payday_window"] = (df["day"] >= 28) | (df["day"] <= 5)

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE dim_date CASCADE"))

    df.to_sql("dim_date", engine, if_exists="append", index=False)

    with engine.begin() as conn:
        total  = conn.execute(text("SELECT COUNT(*) FROM dim_date")).scalar()
        hols   = conn.execute(text("SELECT COUNT(*) FROM dim_date WHERE is_holiday")).scalar()
        paydays = conn.execute(text("SELECT COUNT(*) FROM dim_date WHERE payday_window")).scalar()

    print(f"✓ dim_date populated: {total} rows  "
          f"({hols} holidays · {paydays} payday-window days)")


if __name__ == "__main__":
    main()
