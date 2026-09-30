#!/usr/bin/env python3
"""Build the additive Delta table `acme_sports.demo.contract_economics` for the AI Contract
& FFP/PSR Compliance Agent: per-player financial inputs used to model wage-bill headroom,
transfer-fee amortization, and PSR/FFP squad-cost ratio.

DATA HONESTY: wages + contract dates are the REAL demo `contracts`/`players` data. The
**acquisition fee** (original transfer price) is synthetic — the demo never had purchase
prices — seeded deterministically from the player's book value and tier. Amortization is
then computed transparently (fee / contract length). A live feed swaps the acquisition-fee
column for the club's actual transfer ledger; every other column is already real.
Brand-new additive table — nothing else touched.

Run: python3 scripts/gen_contract_economics.py
"""
import hashlib, os, sys
from datetime import date
sys.path.insert(0, os.path.dirname(__file__))
import dbsql

CAT, SCH = "acme_sports", "demo"
TBL = f"{CAT}.{SCH}.contract_economics"


def _seed(pid, salt):
    return int(hashlib.md5(f"{pid}:{salt}".encode()).hexdigest(), 16) % 1000 / 1000.0


def _years(start, end):
    try:
        s = date.fromisoformat(str(start)); e = date.fromisoformat(str(end))
        return max(1.0, round((e - s).days / 365.25, 1))
    except Exception:
        return 5.0


def _remaining_years(end):
    try:
        e = date.fromisoformat(str(end))
        return max(0.0, round((e - date(2026, 8, 20)).days / 365.25, 1))
    except Exception:
        return 2.0


def main():
    rows = dbsql.query_rows(f"""
      SELECT p.player_id, p.name, p.tier, p.gpv, p.wage_per_yr AS wage,
             c.contract_start, c.contract_end
      FROM {CAT}.{SCH}.players p JOIN {CAT}.{SCH}.contracts c USING(player_id)
      WHERE p.tier='First Team'""")
    recs = []
    for r in rows:
        pid = r["player_id"]; gpv = float(r["gpv"] or 0); wage = float(r["wage"] or 0)
        yrs = _years(r["contract_start"], r["contract_end"])
        rem = _remaining_years(r["contract_end"])
        # synthetic acquisition fee: academy/homegrown ~0; others ~55-85% of current book value
        if gpv <= 0:
            fee = 0.0
        else:
            fee = round(gpv * (0.55 + 0.30 * _seed(pid, "fee")), 1)
        amort = round(fee / yrs, 2) if yrs else 0.0
        residual = round(max(0.0, amort * rem), 1)   # unamortized book value remaining
        recs.append({"player_id": pid, "name": r["name"], "acquisition_fee": fee,
                     "contract_years": yrs, "remaining_years": rem, "annual_wage": wage,
                     "annual_amortization": amort, "residual_book_value": residual,
                     "annual_squad_cost": round(wage + amort, 2)})

    dbsql.run(f"DROP TABLE IF EXISTS {TBL}")
    dbsql.run(f"""CREATE TABLE {TBL} (
        player_id STRING, name STRING, acquisition_fee DOUBLE, contract_years DOUBLE,
        remaining_years DOUBLE, annual_wage DOUBLE, annual_amortization DOUBLE,
        residual_book_value DOUBLE, annual_squad_cost DOUBLE)
        COMMENT 'AI FFP/PSR agent — per-player contract economics: real wages/dates + synthetic acquisition fee -> amortization'""")
    q = lambda s: str(s).replace("'", "''")
    for r in recs:
        dbsql.run(f"INSERT INTO {TBL} VALUES ('{r['player_id']}', '{q(r['name'])}', {r['acquisition_fee']}, "
                  f"{r['contract_years']}, {r['remaining_years']}, {r['annual_wage']}, "
                  f"{r['annual_amortization']}, {r['residual_book_value']}, {r['annual_squad_cost']})")
    tot_wage = sum(r["annual_wage"] for r in recs)
    tot_amort = sum(r["annual_amortization"] for r in recs)
    print(f"contract_economics: wrote {len(recs)} first-team rows")
    print(f"  wage bill €{tot_wage:.1f}M/yr · amortization €{tot_amort:.1f}M/yr · annual squad cost €{tot_wage+tot_amort:.1f}M")


if __name__ == "__main__":
    main()
