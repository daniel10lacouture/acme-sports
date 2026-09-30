"""AI Contract & FFP/PSR Compliance Agent (exec-focused).

Models wage-bill headroom, transfer-fee amortization and PSR/FFP squad-cost headroom from the
real `contracts`/`players` data + the synthetic `contract_economics` acquisition fees, and
surfaces the governed contract PDFs (the `contract_files` FILE-column table) as evidence. A LIVE
`ai_query` writes the board-level summary. Flags the risks that actually move compliance:
expiring deals (free-transfer risk), wage concentration, high residual book value.

Club financial assumptions are ILLUSTRATIVE and labelled as such; the model is transparent
(every figure is derived, not black-box). Production path: wire revenue/opex to the finance
ledger — the ratios recompute unchanged.
"""
import json
from server import dbx

CAT, SCH = dbx.CATALOG, dbx.SCHEMA
FFP_ENDPOINT = "databricks-gpt-5-mini"

# ---- illustrative club financial assumptions (one-swap to the finance ledger) ----
REVENUE_EUR_M = 320.0          # annual operating revenue
UEFA_SQUAD_COST_LIMIT = 0.70   # UEFA squad-cost ratio cap (wages+amort+agent) / revenue
AGENT_FEE_PCT = 0.08           # agent fees ~ 8% of wage bill
OTHER_OPEX_EUR_M = 95.0        # non-squad opex (matchday, staff, facilities)
PSR_ALLOWABLE_LOSS_EUR_M = 125.0  # ~£105m PL PSR 3-year allowable loss


def _esc(s):
    return str(s).replace("'", "")


def _economics():
    rows = dbx.query(f"""
      SELECT e.player_id, e.name, e.acquisition_fee, e.contract_years, e.remaining_years,
             e.annual_wage, e.annual_amortization, e.residual_book_value, e.annual_squad_cost,
             c.contract_end, c.transfer_status
      FROM {CAT}.{SCH}.contract_economics e
      LEFT JOIN {CAT}.{SCH}.contracts c USING(player_id)
      ORDER BY e.annual_squad_cost DESC""")
    return rows


def _flags(econ):
    flags = []
    for r in econ:
        rem = float(r.get("remaining_years") or 0)
        wage = float(r.get("annual_wage") or 0)
        resid = float(r.get("residual_book_value") or 0)
        if rem <= 1.5:
            flags.append({"player": r["name"], "type": "Expiring deal",
                          "detail": f"{rem:.1f}y left — renew or sell to avoid a free-transfer loss.",
                          "severity": "high" if rem <= 1.0 else "medium"})
        if wage >= 12:
            flags.append({"player": r["name"], "type": "Wage concentration",
                          "detail": f"€{wage:.0f}M/yr — top-band earner weighting the wage bill.",
                          "severity": "medium"})
        if resid >= 45:
            flags.append({"player": r["name"], "type": "High book value",
                          "detail": f"€{resid:.0f}M unamortized — a sale books a large profit/loss swing.",
                          "severity": "low"})
    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(flags, key=lambda f: order.get(f["severity"], 3))[:8]


def summary():
    """Club-level FFP/PSR position + per-player economics + risk flags (no LLM)."""
    econ = _economics()
    wage_bill = round(sum(float(r["annual_wage"] or 0) for r in econ), 1)
    amort = round(sum(float(r["annual_amortization"] or 0) for r in econ), 1)
    agent = round(wage_bill * AGENT_FEE_PCT, 1)
    squad_cost = round(wage_bill + amort + agent, 1)
    ratio = round(squad_cost / REVENUE_EUR_M, 3)
    limit_cost = round(UEFA_SQUAD_COST_LIMIT * REVENUE_EUR_M, 1)
    headroom = round(limit_cost - squad_cost, 1)
    annual_pl = round(REVENUE_EUR_M - (squad_cost + OTHER_OPEX_EUR_M), 1)
    psr_3yr = round(annual_pl * 3, 1)
    psr_headroom = round(PSR_ALLOWABLE_LOSS_EUR_M + psr_3yr, 1)
    return {
        "assumptions": {"revenue_eur_m": REVENUE_EUR_M, "uefa_limit_pct": UEFA_SQUAD_COST_LIMIT,
                        "agent_fee_pct": AGENT_FEE_PCT, "other_opex_eur_m": OTHER_OPEX_EUR_M,
                        "psr_allowable_loss_eur_m": PSR_ALLOWABLE_LOSS_EUR_M},
        "wage_bill": wage_bill, "amortization": amort, "agent_fees": agent,
        "squad_cost": squad_cost, "squad_cost_ratio": ratio, "limit_cost": limit_cost,
        "investment_headroom": headroom, "annual_pl": annual_pl, "psr_3yr_projection": psr_3yr,
        "psr_headroom": psr_headroom,
        "compliant": headroom >= 0 and psr_headroom >= 0,
        "players": econ, "flags": _flags(econ),
    }


# ---- forward-looking scenarios (illustrative / synthetic, clearly labelled) ----
UCL_REVENUE_UPLIFT_EUR_M = 65.0   # illustrative CL participation uplift (broadcast + gate + prize)
GBP_EUR = 1.17                    # illustrative FX for the £/wk renewal example


def scenarios():
    """Three forward-looking, illustrative FFP/PSR what-ifs off the current position."""
    s = summary()
    rev, cap, sc = REVENUE_EUR_M, UEFA_SQUAD_COST_LIMIT, s["squad_cost"]

    def pack(rev_, sc_):
        lim = round(cap * rev_, 1)
        return {"revenue": round(rev_, 1), "squad_cost": round(sc_, 1),
                "ratio": round(sc_ / rev_, 3), "limit_cost": lim,
                "headroom": round(lim - sc_, 1),
                "annual_pl": round(rev_ - (sc_ + OTHER_OPEX_EUR_M), 1)}

    # 1) Champions League participation revenue — with vs without qualification
    with_ucl = pack(rev, sc)
    without_ucl = pack(rev - UCL_REVENUE_UPLIFT_EUR_M, sc)
    ucl = {"uplift_eur_m": UCL_REVENUE_UPLIFT_EUR_M, "with_ucl": with_ucl,
           "without_ucl": without_ucl,
           "headroom_swing": round(with_ucl["headroom"] - without_ucl["headroom"], 1)}

    # 2) New-signing impact — an illustrative marquee signing's fee + wages
    fee, wage, years = 90.0, 12.0, 5
    add_amort = round(fee / years, 1)
    add_agent = round(wage * AGENT_FEE_PCT, 1)
    add_cost = round(add_amort + wage + add_agent, 1)
    signing = {"name": "Julián Álvarez (illustrative target)", "fee_eur_m": fee,
               "wage_eur_m": wage, "years": years, "added_amortization": add_amort,
               "added_agent": add_agent, "added_squad_cost": add_cost,
               "before": pack(rev, sc), "after": pack(rev, sc + add_cost)}

    # 3) Contract-renewal impact — Max Dowman £10k/wk -> £50k/wk
    wk_before, wk_after = 10, 50   # £k / week
    wage_before = round(wk_before * 52 / 1000.0 * GBP_EUR, 2)   # -> €M/yr
    wage_after = round(wk_after * 52 / 1000.0 * GBP_EUR, 2)
    add_wage = round(wage_after - wage_before, 2)
    ren_cost = round(add_wage * (1 + AGENT_FEE_PCT), 2)
    renewal = {"player": "Max Dowman", "wk_before_gbp_k": wk_before, "wk_after_gbp_k": wk_after,
               "wage_before_eur_m": wage_before, "wage_after_eur_m": wage_after,
               "added_wage_eur_m": add_wage, "added_squad_cost": ren_cost,
               "before": pack(rev, sc), "after": pack(rev, sc + ren_cost)}

    return {"assumptions": {"ucl_uplift_eur_m": UCL_REVENUE_UPLIFT_EUR_M, "gbp_eur": GBP_EUR,
                            "revenue_eur_m": rev, "uefa_limit_pct": cap},
            "base": pack(rev, sc), "ucl": ucl, "signing": signing, "renewal": renewal}


def contract_evidence(limit=3):
    """Governed contract PDFs (FILE-column table) as evidence, highest squad-cost first."""
    try:
        return dbx.query(f"""
          SELECT f.player_name, f.file_uri, f.ai_summary
          FROM {CAT}.{SCH}.contract_files f
          JOIN {CAT}.{SCH}.contract_economics e ON e.player_id = f.player_id
          WHERE f.ai_summary IS NOT NULL
          ORDER BY e.annual_squad_cost DESC LIMIT {int(limit)}""")
    except Exception:
        return []


def exec_brief():
    """LIVE ai_query board-level narrative grounded in the computed compliance position."""
    s = summary()
    top_flags = "; ".join(f"{f['player']}: {f['type']} ({f['detail']})" for f in s["flags"][:4])
    facts = (
        f"Revenue €{REVENUE_EUR_M}M. Wage bill €{s['wage_bill']}M, transfer amortization €{s['amortization']}M, "
        f"agent fees €{s['agent_fees']}M -> annual squad cost €{s['squad_cost']}M. "
        f"UEFA squad-cost ratio {s['squad_cost_ratio']*100:.0f}% vs {UEFA_SQUAD_COST_LIMIT*100:.0f}% cap "
        f"(investment headroom €{s['investment_headroom']}M). "
        f"Projected annual P&L €{s['annual_pl']}M; PSR 3-year headroom €{s['psr_headroom']}M "
        f"(allowable loss €{PSR_ALLOWABLE_LOSS_EUR_M}M). Key risks: {top_flags}."
    )
    prompt = (
        "You are the club's CFO briefing the board on FFP/PSR compliance. Using ONLY these figures, write "
        "STRICT JSON with keys: verdict (one of 'Compliant','Watch','At risk'), "
        "headline (one sentence), so_what (2 sentences on what it means for the transfer window), "
        "recommendation (one specific action). No text outside the JSON. Figures: " + facts
    )
    rows = dbx.query(f"SELECT ai_query('{FFP_ENDPOINT}', '{_esc(prompt)}') AS r")
    raw = rows[0]["r"] if rows else ""
    brief = _parse_json(raw)
    return {"summary": s, "brief": brief, "raw": None if brief else raw,
            "evidence": contract_evidence(), "source": f"ai_query · {FFP_ENDPOINT}"}


def _parse_json(raw):
    if not raw:
        return None
    t = raw.strip(); a, b = t.find("{"), t.rfind("}")
    if a >= 0 and b > a:
        try:
            return json.loads(t[a:b + 1])
        except Exception:
            return None
    return None
