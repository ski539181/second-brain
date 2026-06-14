#!/usr/bin/env python3
"""
ab_test_vol2.py - A/B test: vol2 context vs no context
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, '/root/.hermes/scripts')
from llm_helper import llm_call

# Load vol2 (smaller chunk — multi-domain, more diverse)
DS = Path('/root/.hermes/cache/documents/doc_e34497812434_advanced-coding-dataset-20-vol2.md')
DATASET = DS.read_text()[:6000] if DS.exists() else ""  # first 2 entries

QUESTIONS = [
    "อธิบาย Raft consensus algorithm แบบสั้นๆ",
    "Lock-free queue ใช้ CAS pattern ยังไง",
    "Merkle tree ใช้ทำอะไรใน distributed system",
    "HyperLogLog นับ unique items ได้อย่างไร",
    "Persistent data structure ต่างจาก immutable ยังไง",
]

def score(r):
    code = sum(1 for l in r.split('\n') if l.strip().startswith(('def','class','const','let','function','import','export','await','return')))
    thai = any('\u0E00' <= c <= '\u0E7F' for c in r)
    code_block = '```' in r or 'function' in r
    long_enough = len(r) > 200
    return {"length":len(r),"code_lines":code,"has_code":code_block,"has_thai":thai,
            "score":min(100,code*5+(50 if code_block else 0)+(20 if thai else 0)+(10 if long_enough else 0))}

def main():
    t0 = time.time()
    print(f"🧪 A/B Test — vol2 (multi-domain) context effect\n")
    print(f"Dataset: {len(DATASET)} chars | Questions: {len(QUESTIONS)}\n")
    results = []
    for i, q in enumerate(QUESTIONS, 1):
        a = llm_call(f"Answer concisely in Thai+code:\n\n{q}", max_tokens=400)
        b = llm_call(f"Use this reference:\n\n{DATASET}\n\n---\nAnswer concisely in Thai+code:\n\n{q}", max_tokens=400)
        sa, sb = score(a), score(b)
        d = sb["score"] - sa["score"]
        w = "B" if d>0 else ("A" if d<0 else "TIE")
        results.append((q,sa,sb,d,w))
        print(f"  Q{i}: {q[:45]}...")
        print(f"     A: {sa['score']:3d} ({sa['length']:4d}c, {sa['code_lines']} code)")
        print(f"     B: {sb['score']:3d} ({sb['length']:4d}c, {sb['code_lines']} code)")
        print(f"     Winner: {w} (Δ {d:+d})\n")
        if time.time()-t0 > 480: break
    a_t = sum(r[1]['score'] for r in results)
    b_t = sum(r[2]['score'] for r in results)
    aw = sum(1 for r in results if r[4]=='A')
    bw = sum(1 for r in results if r[4]=='B')
    elapsed = time.time()-t0
    print(f"📊 Results ({elapsed:.0f}s): A={a_t} B={b_t} | A wins {aw}/5 | B wins {bw}/5")
    if b_t > a_t*1.05: print(f"  ✅ B wins {((b_t-a_t)/a_t*100):.0f}%")
    elif a_t > b_t*1.05: print(f"  ❌ A wins {((a_t-b_t)/b_t*100):.0f}%")
    else: print(f"  ⚖️  TIE")

if __name__ == "__main__": main()
