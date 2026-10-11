#!/usr/bin/env python3
"""Full-catalog IPA audit: Wiktionary + Cambridge + ipa-dict tiebreaker.
Outputs only — does not mutate overrides or trigger TTS.

Usage:
  python3 scripts/audit_all_phonetics.py --output-dir output/all-ipa-audit
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


# --- Load all catalog words ---

def load_all_words() -> list[str]:
    """Collect every word from vocabulary_data JSON and CSV."""
    import glob
    words = set()
    for fp in glob.glob(str(REPO_ROOT / "vocabulary_data" / "*.json")):
        try:
            with open(fp) as f:
                d = json.load(f)
        except Exception:
            continue
        if not isinstance(d, dict) or "chapters" not in d:
            continue
        for chap in d.get("chapters") or []:
            for w in chap.get("words") or []:
                wd = (w.get("word") or "").strip().lower()
                if wd:
                    words.add(wd)
    # CSVs
    for fp in glob.glob(str(REPO_ROOT / "vocabulary_data" / "*.csv")):
        try:
            with open(fp, newline="") as f:
                rdr = csv.DictReader(f)
                for row in rdr:
                    wd = (row.get("word") or "").strip().lower()
                    if wd:
                        words.add(wd)
        except Exception:
            continue
    return sorted(words)


# --- Wiktionary ---

def parse_wikt(wt: str) -> dict:
    en_idx = wt.find("==English==")
    en_section = wt[en_idx:en_idx + 15000] if en_idx >= 0 else wt[:15000]
    rp = ga = first_default = None
    for m in re.finditer(r"\{\{IPA\|en\|((?:/[^/]+/\|?)+)([^}]*)\}\}", en_section):
        ipa_part = m.group(1)
        rest = m.group(2)
        ipas = re.findall(r"(/[^/]+/)", ipa_part)
        label_m = re.search(r"a=([^|}]+)", rest)
        label = label_m.group(1).strip() if label_m else ""
        has_rp = any(t in label for t in ("RP", "non-rhotic", "SSB", "Cockney", "Geordie", "Received Pronunciation"))
        has_ga = any(t in label for t in ("GA", "GenAm", "General American", "AAVE", "Rhotic", "Inland North"))
        for ipa in ipas:
            if not label:
                if first_default is None:
                    first_default = ipa
            elif has_rp and not has_ga and rp is None:
                rp = ipa
            elif has_ga and not has_rp and ga is None:
                ga = ipa
            elif has_rp and has_ga:
                if rp is None:
                    rp = ipa
                elif ga is None:
                    ga = ipa
            elif "," in label and rp is None:
                rp = ipa
    if rp is None:
        rp = first_default
    return {"rp": rp, "ga": ga}


def fetch_wikt_batch(words: list[str]) -> dict[str, dict]:
    url = "https://en.wiktionary.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "titles": "|".join(words), "prop": "revisions",
        "rvprop": "content", "format": "json", "redirects": 1,
    })
    req = urllib.request.Request(url, headers={"User-Agent": "ielts-vocab-audit/1.0 (research)"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
    except Exception as e:
        return {"_error": str(e)[:200]}
    pages = data.get("query", {}).get("pages", {})
    out = {}
    for pid, page in pages.items():
        if "missing" in page:
            continue
        title = page.get("title", "").lower()
        revs = page.get("revisions", [])
        if not revs:
            continue
        out[title] = parse_wikt(revs[0].get("*", ""))
    return out


# --- Cambridge ---

def fetch_cambridge(word: str) -> dict | None:
    url = f"https://dictionary.cambridge.org/dictionary/english/{urllib.parse.quote(word)}"
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
                "Accept": "text/html,application/xhtml+xml",
            })
            with urllib.request.urlopen(req, timeout=8) as r:
                html = r.read().decode("utf-8", errors="ignore")
            break
        except Exception:
            if attempt == 0:
                time.sleep(1.0)
            else:
                return None
    uk_ipa, us_ipa = None, None
    for region_match in re.finditer(r'<span class="region dreg">(\w+)</span>', html):
        region = region_match.group(1).lower()
        if region not in ("uk", "us"):
            continue
        rest = html[region_match.end():region_match.end() + 2000]
        ipa_match = re.search(r'<span class="ipa dipa lpr-2 lpl-1">(.*?)</span>', rest, re.S)
        if not ipa_match:
            continue
        clean = re.sub(r"<[^>]+>", "", ipa_match.group(1))
        if not clean.startswith("/"):
            clean = "/" + clean.strip() + "/"
        if region == "uk" and uk_ipa is None:
            uk_ipa = clean
        elif region == "us" and us_ipa is None:
            us_ipa = clean
    return {"uk": uk_ipa, "us": us_ipa}


# --- Normalize ---

def normalize(ipa: str) -> str:
    if not ipa:
        return ""
    s = ipa
    s = s.replace(".", "").replace("͡", "").replace("ː", "").replace("ˑ", "")
    s = s.replace("ɹ", "r").replace("ᵊ", "ə")
    s = s.replace("ˈ", "").replace("ˌ", "")
    s = s.replace("(r)", "r").replace("(ə)", "ə")
    return s.lower().strip("/").strip()


# --- ipa-dict ---

def load_ipa_dict(path: Path) -> dict[str, str]:
    out = {}
    if not path.exists():
        return out
    with open(path) as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 2:
                w = parts[0].strip().lower()
                ipa = parts[1].strip().split(",")[0].strip()
                if w and ipa and w not in out:
                    out[w] = ipa
    return out


# --- Checkpoint ---

def load_checkpoint(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return {}
    return {}


def save_checkpoint(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


# --- Main ---

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="output/all-ipa-audit")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--cambridge-delay", type=float, default=0.5)
    parser.add_argument("--wikt-delay", type=float, default=0.3)
    parser.add_argument("--ipa-dict-path", default="tmp/ipa-audit/ipa-dict-en-us.txt")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--start-from", type=int, default=0,
                        help="Skip first N words (use with --no-resume to override checkpoint)")
    args = parser.parse_args()

    out_dir = REPO_ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = out_dir / "checkpoint.json"
    csv_path = out_dir / "all-words-audit.csv"

    print("Loading catalog words...", flush=True)
    all_words = load_all_words()
    if args.start_from > 0:
        all_words = all_words[args.start_from:]
        print(f"  Starting from index {args.start_from}: {len(all_words)} remaining", flush=True)
    if args.limit > 0:
        all_words = all_words[:args.limit]
    print(f"  Total: {len(all_words)} words", flush=True)

    state = load_checkpoint(checkpoint_path) if args.resume else {}
    done = set(state.get("done_words", []))
    rows = state.get("rows", [])

    print("Loading ipa-dict tiebreaker...", flush=True)
    ipa_dict = load_ipa_dict(REPO_ROOT / args.ipa_dict_path)
    print(f"  ipa-dict entries: {len(ipa_dict)}", flush=True)

    pending = [w for w in all_words if w not in done]
    print(f"Already done: {len(done)}, pending: {len(pending)}", flush=True)

    csv_file = open(csv_path, "w", newline="")
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow([
        "word", "wikt_rp", "wikt_ga", "camb_uk", "camb_us", "ipa_dict",
        "wikt_rp_norm", "camb_uk_norm", "ipa_dict_norm",
        "uk_agreement", "us_agreement", "any_agreement", "agreeing_sources",
    ])
    for r in rows:
        csv_writer.writerow(r)
    csv_file.flush()

    t0 = time.time()
    for i in range(0, len(pending), args.batch_size):
        batch = pending[i:i + args.batch_size]
        wikt = fetch_wikt_batch(batch)
        time.sleep(args.wikt_delay)
        for w in batch:
            camb = fetch_cambridge(w)
            time.sleep(args.cambridge_delay)
            wk = wikt.get(w, {"rp": None, "ga": None})
            cb = camb or {"uk": None, "us": None}
            id_ipa = ipa_dict.get(w, "")
            wk_rp_n = normalize(wk.get("rp", ""))
            wk_ga_n = normalize(wk.get("ga", ""))
            cb_uk_n = normalize(cb.get("uk", ""))
            cb_us_n = normalize(cb.get("us", ""))
            id_n = normalize(id_ipa)
            # UK agreement: Wiktionary RP vs Cambridge UK
            uk_agree = ""
            if wk_rp_n and cb_uk_n:
                uk_agree = "agree" if wk_rp_n == cb_uk_n else "disagree"
            elif wk_rp_n or cb_uk_n:
                uk_agree = "single"
            else:
                uk_agree = "missing"
            # US agreement: Wiktionary GA vs Cambridge US
            us_agree = ""
            if wk_ga_n and cb_us_n:
                us_agree = "agree" if wk_ga_n == cb_us_n else "disagree"
            elif wk_ga_n or cb_us_n:
                us_agree = "single"
            else:
                us_agree = "missing"
            # Any 2-source agreement
            agrees = []
            if wk_rp_n and cb_uk_n and wk_rp_n == cb_uk_n:
                agrees.append("W=C(UK)")
            if wk_ga_n and cb_us_n and wk_ga_n == cb_us_n:
                agrees.append("W=C(US)")
            if wk_rp_n and id_n and wk_rp_n == id_n:
                agrees.append("W=I")
            if cb_uk_n and id_n and cb_uk_n == id_n:
                agrees.append("C=I")
            any_agree = "yes" if agrees else "no"
            row = [
                w, wk.get("rp") or "", wk.get("ga") or "",
                cb.get("uk") or "", cb.get("us") or "", id_ipa,
                wk_rp_n, cb_uk_n, id_n,
                uk_agree, us_agree, any_agree, "|".join(agrees),
            ]
            csv_writer.writerow(row)
            rows.append(row)
        # Save checkpoint every batch
        save_checkpoint(checkpoint_path, {"done_words": list(set(done) | set(batch)), "rows": rows})
        csv_file.flush()
        done_batch = min(i + len(batch), len(pending))
        elapsed = time.time() - t0
        rate = (i + len(batch)) / elapsed if elapsed > 0 else 0
        eta = (len(pending) - done_batch) / rate if rate > 0 else 0
        print(f"  {done_batch}/{len(pending)}  elapsed={elapsed:.0f}s  rate={rate:.1f}/s  eta={eta:.0f}s", flush=True)

    csv_file.close()
    # Summary
    uk_stats = Counter(r[9] for r in rows)
    us_stats = Counter(r[10] for r in rows)
    any_stats = Counter(r[11] for r in rows)
    print(f"\n=== UK agreement ===")
    for k, v in uk_stats.most_common():
        print(f"  {k}: {v}")
    print(f"\n=== US agreement ===")
    for k, v in us_stats.most_common():
        print(f"  {k}: {v}")
    print(f"\n=== Any 2-source agreement ===")
    for k, v in any_stats.most_common():
        print(f"  {k}: {v}")
    print(f"\nCSV: {csv_path}")


if __name__ == "__main__":
    main()
