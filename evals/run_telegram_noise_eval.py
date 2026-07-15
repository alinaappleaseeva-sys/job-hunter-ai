#!/usr/bin/env python3
"""Small Telegram noise / relevance eval for Wave 1 (tuned filters).

Run:
    PYTHONPATH=src python evals/run_telegram_noise_eval.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from job_hunter_ai.connectors.telegram import (
    is_telegram_job_signal,
    score_telegram_message,
)
from job_hunter_ai.connectors.telegram_channels import (
    get_wave1_channels,
    load_sample_for_channel,
)

# Extended set with new messages for tuned eval (including new channels)
EXTRA_EVAL_MESSAGES = [
    # Good - strong segment + seniority
    {"channel": "web3hiring", "text": "Head of Ops @ new L2 DAO. Remote. Treasury and governance experience required.", "expected": "good"},
    {"channel": "dejob_global", "text": "Senior Operations Lead - DAO. Full remote, async. Treasury Ops big plus.", "expected": "good"},
    {"channel": "cryptojobslist", "text": "DAO Ops Manager position. Must have on-chain governance experience.", "expected": "good"},
    {"channel": "web3jobs", "text": "Governance Lead at growing protocol. Contributor coordination and treasury.", "expected": "good"},
    {"channel": "web3hiring", "text": "Program Manager - On-Chain Operations. Remote.", "expected": "good"},

    # Borderline but good
    {"channel": "cryptohiring_1", "text": "Hiring: Head of Operations for fast-growing DeFi. Web3 experience required.", "expected": "good"},
    {"channel": "dejob_global", "text": "Treasury Operations role in DAO. Remote.", "expected": "good"},

    # Pure noise - dev
    {"channel": "web3hiring", "text": "Hiring Senior Solidity Engineer. Remote only. Must have 5+ years.", "expected": "noise"},
    {"channel": "cryptojobslist", "text": "Smart Contract Developer - Rust. Full remote.", "expected": "noise"},
    {"channel": "web3jobs", "text": "Frontend Engineer for Web3 startup.", "expected": "noise"},

    # Noise - marketing/community
    {"channel": "dejob_global", "text": "Looking for community manager. DM for details", "expected": "noise"},
    {"channel": "web3hiring", "text": "Growth Marketing Lead - Web3 project.", "expected": "noise"},

    # Non-hiring
    {"channel": "smerkisjobs", "text": "General crypto market discussion, no openings", "expected": "noise"},
    {"channel": "cryptojobslist", "text": "Airdrop alert - join our TG for signals", "expected": "noise"},

    # Additional good
    {"channel": "web3jobs", "text": "Contributor Coordinator - DAO. Must understand Snapshot and on-chain voting.", "expected": "good"},
    {"channel": "cryptojobslist", "text": "DAO Finance & Ops Lead. Remote, competitive comp + tokens.", "expected": "good"},
    {"channel": "dejob_global", "text": "On-Chain Operations Manager needed. Governance experience preferred.", "expected": "good"},
]

def main():
    channels = get_wave1_channels()
    print("=== Wave 1 Telegram Noise Eval (tuned filters) ===\n")
    print("Channels evaluated:", list(channels.keys()))
    print()

    all_results = []
    total = 0
    passed_filter = 0
    high_score = 0
    has_segment = 0
    false_positives = []

    for ch in channels:
        samples = load_sample_for_channel(ch)
        for msg in samples:
            text = msg.get("text") or msg.get("message", "")
            passed = is_telegram_job_signal(text)
            sc = score_telegram_message(text)
            all_results.append({
                "channel": ch,
                "text": text[:85],
                "passed": passed,
                "score": sc["score"],
                "has_segment": sc["has_segment"],
            })
            total += 1
            if passed: passed_filter += 1
            if sc["score"] > 0.7: high_score += 1
            if sc["has_segment"]: has_segment += 1

    for ex in EXTRA_EVAL_MESSAGES:
        text = ex["text"]
        passed = is_telegram_job_signal(text)
        sc = score_telegram_message(text)
        all_results.append({
            "channel": ex["channel"],
            "text": text[:85],
            "passed": passed,
            "score": sc["score"],
            "has_segment": sc["has_segment"],
            "expected": ex.get("expected"),
        })
        total += 1
        if passed: passed_filter += 1
        if sc["score"] > 0.7: high_score += 1
        if sc["has_segment"]: has_segment += 1
        if ex.get("expected") == "noise" and passed:
            false_positives.append((ex["channel"], text[:70]))

    job_rate = passed_filter / total if total else 0
    seg_rate = has_segment / total if total else 0
    high_rate = high_score / total if total else 0

    print(f"Total messages: {total}")
    print(f"Passed filter: {passed_filter} ({job_rate:.1%})")
    print(f"High score (>0.7): {high_score} ({high_rate:.1%})")
    print(f"Segment keywords: {has_segment} ({seg_rate:.1%})")
    print(f"False positives (noise that passed): {len(false_positives)}")
    print()

    print("--- Good signals from new channels (web3hiring, dejob_global, cryptojobslist, web3jobs) ---")
    for r in all_results:
        if r["passed"] and r["channel"] in ["web3hiring", "dejob_global", "cryptojobslist", "web3jobs"]:
            print(f"  [{r['channel']}] score={r['score']} | {r['text']}")
    print()

    if false_positives:
        print("--- False positives ---")
        for ch, txt in false_positives[:4]:
            print(f"  [{ch}] {txt}")
        print()

    print("--- Tuning notes ---")
    print("Positive keywords strengthened with Head/Senior/DAO Ops/Treasury Ops etc.")
    print("Score now boosts seniority + domain + remote.")
    print("Next: real Telethon run when confident.")

if __name__ == "__main__":
    main()
