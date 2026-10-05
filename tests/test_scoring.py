import sys
import os

from app.decoder import TOPIC0, decode_log
from app.scoring import ScoreEvent, Config, score, max_raw_with_liquidations
from app.validate import compare

def w(x): return format(x, "064x")
def t(a): return "0x" + a[2:].rjust(64, "0")
RES="0x"+"11"*20; ME="0x"+"aa"*20; ROUTER="0x"+"bb"*20; LIQ="0x"+"cc"*20
base = dict(blockNumber="0x10", transactionHash="0xabc", logIndex="0x1")

def test_topic_hashes_known():
    # widely published Aave V3 topic0 hashes
    assert TOPIC0["Supply"] == "0x2b627736bca15cd5381dcf80b0bf11fd197d01a037c52b927a881a10fb73ba61"
    assert TOPIC0["Borrow"] == "0xb3d084820fb1a9decffb176436bd02558d15fac9b0ddfed8c465bc7359d7dce0"
    assert TOPIC0["Repay"] == "0xa534c8dbe71f871f9f3530e97a74601fea17b426cae02e1c5aee42c96c784051"
    assert TOPIC0["LiquidationCall"] == "0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286"

def test_supply_attribution_onbehalfof():
    log = dict(topics=[TOPIC0["Supply"], t(RES), t(ME), t("0x0")],
               data="0x" + w(int(ROUTER, 16)) + w(5000), **base)
    e = decode_log(log)
    assert e.account == ME and e.counterparty == ROUTER and e.amount_raw == 5000

def test_repay_credits_debtor_not_payer():
    log = dict(topics=[TOPIC0["Repay"], t(RES), t(ME), t(ROUTER)], data="0x" + w(42) + w(0), **base)
    e = decode_log(log)
    assert e.account == ME and e.counterparty == ROUTER

def test_liquidation_hits_borrower():
    log = dict(topics=[TOPIC0["LiquidationCall"], t(RES), t("0x"+"22"*20), t(ME)],
               data="0x" + w(7) + w(9) + w(int(LIQ, 16)) + w(0), **base)
    e = decode_log(log)
    assert e.account == ME and e.counterparty == LIQ and e.amount_raw == 7

D = 86400
def test_dust_and_daily_limit():
    ev = [ScoreEvent("Repay", i*100, "USDC", 1.0) for i in range(500)]      # dust, same day
    assert score(ev, 10**6).components["repay"] == 0
    ev = [ScoreEvent("Repay", i*100, "USDC", 500.0) for i in range(500)]    # big, same day
    assert score(ev, 10**6).components["repay"] == 25                       # one per asset-day
    assert score(ev, 10**6, Config(daily_limit=False)).components["repay"] == 150

def test_thin_file_gate():
    ev = [ScoreEvent("Supply", 0, "USDC", 1.0)]  # dust supply counts as a lending interaction
    far = 10 * 365 * D
    assert score([], far).final == 300
    assert score([], far, Config(thin_file_gate=False)).components["age"] == 0  # no events at all: nothing to age

def test_cap_is_vacuous_under_paper_weights():
    # Force original V1 weights to prove the mathematical flaw
    cfg = Config(base=300, repay_cap=150, supply_cap=60, month_cap=60, age_cap=60, liq_penalty=200, liq_cap_score=600)
    assert max_raw_with_liquidations(cfg, 1) == 430 < cfg.liq_cap_score
    assert max_raw_with_liquidations(cfg, 0) == 630

def test_cap_binds_with_smaller_penalty():
    # Test the V2 fix where penalty is reduced to 50
    cfg = Config(liq_penalty=50)
    ev = [ScoreEvent("Repay", d*D, "USDC", 500.0) for d in range(0, 400, 31)]  # many months
    ev += [ScoreEvent("Supply", d*D, "WETH", 500.0) for d in range(0, 400, 31)]
    ev.append(ScoreEvent("LiquidationCall", 380*D, "USDC", 100))
    r = score(ev, 390*D, cfg)
    assert r.cap_active and r.final <= 600
    assert score(ev, (380+366)*D, cfg).cap_active is False      # cap decays, event remains
    assert score(ev, (380+366)*D, cfg).components["liquidation"] == -50

def test_validate():
    log = dict(topics=[TOPIC0["Repay"], t(RES), t(ME), t(ROUTER)], data="0x"+w(1)+w(0), **base)
    e = decode_log(log)
    r = compare([e], {(e.tx_hash, e.log_index, "Repay", ME)})
    assert r["precision"] == r["recall"] == 1.0
    r = compare([e], {(e.tx_hash, e.log_index, "Repay", ROUTER)})   # payer wrongly credited by other source
    assert r["attribution_mismatches"] == 1