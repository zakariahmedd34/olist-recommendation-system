"""Step 3 — Populate Dim_Region with the 27 Brazilian states + their macro-region."""
from sqlalchemy import text
from db import engine

BR_MACRO = {
    "AC": "Norte",       "AP": "Norte",       "AM": "Norte",
    "PA": "Norte",       "RO": "Norte",       "RR": "Norte",
    "TO": "Norte",
    "AL": "Nordeste",    "BA": "Nordeste",    "CE": "Nordeste",
    "MA": "Nordeste",    "PB": "Nordeste",    "PE": "Nordeste",
    "PI": "Nordeste",    "RN": "Nordeste",    "SE": "Nordeste",
    "DF": "Centro-Oeste","GO": "Centro-Oeste","MT": "Centro-Oeste",
    "MS": "Centro-Oeste",
    "ES": "Sudeste",     "MG": "Sudeste",     "RJ": "Sudeste",
    "SP": "Sudeste",
    "PR": "Sul",         "RS": "Sul",         "SC": "Sul",
}


def main() -> None:
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE dim_region RESTART IDENTITY CASCADE"))
        for state, region in BR_MACRO.items():
            conn.execute(
                text("INSERT INTO dim_region (state, macro_region) VALUES (:s, :r)"),
                {"s": state, "r": region},
            )
        n = conn.execute(text("SELECT COUNT(*) FROM dim_region")).scalar()
        sample = conn.execute(
            text("SELECT state, macro_region FROM dim_region ORDER BY state LIMIT 5")
        ).all()

    print(f"✓ dim_region populated: {n} rows")
    print("  sample:", sample)


if __name__ == "__main__":
    main()
