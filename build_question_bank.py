#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""汇总所有题库（文字层解析 + OCR解析）→ 前端题库JS。"""
import os, re, json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
OUT_JS = os.path.join(BASE, "js", "data-questions.js")
os.makedirs(os.path.join(BASE, "js"), exist_ok=True)

SUBJECT_ORDER = ["系统解剖学","儿童康复学","肌肉解剖学","康复功能评定学",
                 "人体发育学","神经康复学","物理治疗学","语言治疗学","作业治疗学"]

# 常见 OCR / 文字层误识别修正（修复题干可读性，不改变含义）
TYPO_FIX = {
    "丕眞土":"不属于", "丕昼壬":"不属于", "丕竝":"不属于", "丕虹":"不属于",
    "丕晨壬":"不属于", "下列丕":"下列不", "否层":"属于", "不團于":"不属于",
    "否吕舞":"是", "题骨":"颞骨", "人院":"入院", "人口":"入口",
    "I第一章I":"", "I第": "第", "单•": "单", "•": ".",
}

def clean_stem(s):
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"^[\d\.、•·]+\s*", "", s)
    s = s.strip()
    for a, b in TYPO_FIX.items():
        s = s.replace(a, b)
    # 去除残留的章节标记如 "第一章"
    s = re.sub(r"[IⅠ]第[一二三四五六七八九十百\d]+章[IⅠ]", "", s)
    return s.strip()

def normalize(q):
    """统一字段 -> {type, stem, options, answer, analysis}"""
    t = q["type"]
    if t in ("single", "multi"):
        stem = clean_stem(q.get("stem", ""))
        if not stem or len(stem) > 120 or len(q.get("options", {})) < 3:
            return None
        opts = [q["options"].get(k, "") for k in "ABCDE" if k in q["options"]]
        ans = q.get("answer", "")
        if not ans:
            return None
        return {"type": t, "stem": stem, "options": opts, "answer": ans, "analysis": ""}
    else:
        stem = clean_stem(q.get("text", q.get("stem", "")))
        ans = clean_stem(q.get("answer", ""))
        if not stem or len(stem) > 400 or len(stem) < 2:
            return None
        # 名词解释并入 blank（简答记忆），qa 保留
        typ = "blank" if t == "term" else "qa"
        return {"type": typ, "stem": stem, "answer": ans[:500], "analysis": ""}

def load_text_books():
    raw = json.load(open(os.path.join(DATA, "questions_raw.json"), encoding="utf-8"))
    bank = {s: [] for s in SUBJECT_ORDER}
    name_map = {"人体发育学":"人体发育学","作业治疗学":"作业治疗学",
                "物理治疗学":"物理治疗学","语言治疗学":"语言治疗学",
                "系统解剖学":"系统解剖学","儿童康复学":"儿童康复学",
                "康复功能评定学":"康复功能评定学","神经康复学":"神经康复学",
                "肌肉解剖学":"肌肉解剖学"}
    for q in raw:
        subj = name_map.get(q.get("book", ""))
        if not subj:
            continue
        n = normalize(q)
        if n:
            bank[subj].append(n)
    return bank

def load_ocr_books():
    fp = os.path.join(DATA, "questions_ocr.json")
    if not os.path.exists(fp):
        return {s: [] for s in SUBJECT_ORDER}
    raw = json.load(open(fp, encoding="utf-8"))
    bank = {s: [] for s in SUBJECT_ORDER}
    for q in raw:
        subj = q.get("subject", "")
        if subj not in bank:
            continue
        n = normalize(q)
        if n:
            bank[subj].append(n)
    return bank

def dedup(questions):
    seen, out = set(), []
    for q in questions:
        key = (q["type"], q["stem"][:45])
        if key in seen:
            continue
        seen.add(key)
        # 选择题选项去重后需 >=3 且不重复
        if q["type"] in ("single", "multi"):
            opts = [o for o in q["options"] if o.strip()]
            if len(opts) < 3 or len(set(opts)) < 2:
                continue
        out.append(q)
    return out

def main():
    a = load_text_books()
    b = load_ocr_books()
    bank = {}
    for s in SUBJECT_ORDER:
        qs = dedup(a[s] + b[s])
        bank[s] = qs
        from collections import Counter
        c = Counter(q["type"] for q in qs)
        print(f"{s}: {len(qs)} 题 {dict(c)}")
    # 输出JS
    with open(OUT_JS, "w", encoding="utf-8") as f:
        f.write("// 康复君题库数据（由习题资料提取生成）\n")
        f.write("const QUESTION_BANK = ")
        json.dump(bank, f, ensure_ascii=False)
        f.write(";\n")
    total = sum(len(v) for v in bank.values())
    print(f"总题量 {total} -> {OUT_JS}")

if __name__ == "__main__":
    main()
