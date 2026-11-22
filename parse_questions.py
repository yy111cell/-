#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用题目解析器：从 OCR/文字层文本中提取 选择题/名词解释/问答题/填空题，按题号与参考答案配对。"""
import os, re, json, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TXT = os.path.join(BASE, "data", "txt")
OCR = os.path.join(BASE, "data", "ocr")
OUT = os.path.join(BASE, "data", "questions_raw.json")

# 归一化：全角标点、OCR 常见误识别
TRANS = str.maketrans({
    "．": ".", "，": ",", "：": ":", "（": "(", "）": ")", "【": "[", "】": "]",
    "？": "?", "；": ";", "“": '"', "”": '"',
})

def clean(s):
    s = s.translate(TRANS)
    s = re.sub(r"[ \t]+", " ", s).strip()
    return s

# 题型识别关键词（顺序敏感）
SECTION_PATTERNS = [
    ("choice", r"(?:单选题|选择题|最佳选择题|A1\s*型题|A2\s*型题|\[A[123]型题\])"),
    ("multi",  r"(?:多选题|X\s*型题|多项选择题|\[X型题\])"),
    ("blank",  r"(?:填空题)"),
    ("term",   r"(?:名词解释)"),
    ("qa",     r"(?:问答题|简答题|论述题)"),
]
ANSWER_TAIL = re.compile(r"参\s*考\s*答\s*案|答\s*案")

# 题号行：1. 1、 1 (1)  (支持 OCR 把 . 识别成 • 等)
QNUM = re.compile(r"^\s*(\d{1,3})\s*[\.．、,•·:：]\s*")
# 选项行
OPT = re.compile(r"^\s*([A-Ea-e])\s*[\.．、:：]?\s*(.*)$")
# 答案区的选择题答案： 1. E  或 1.E 2.B 或 & D(OCR错误)
ANS_CHOICE_INLINE = re.compile(r"(\d{1,3})\s*[\.．、]\s*([A-Ea-e]{1,5})\b")


def split_sections(lines):
    """把行列表按题型标记切成 [(type, [lines]), ...]"""
    sections = []
    cur = None
    buf = []
    for ln in lines:
        matched = None
        for typ, pat in SECTION_PATTERNS:
            if re.search(pat, ln) and len(ln) < 40:
                matched = typ
                break
        if matched:
            if cur is not None:
                sections.append((cur, buf))
            cur = matched
            buf = []
        else:
            if cur is not None:
                buf.append(ln)
    if cur is not None:
        sections.append((cur, buf))
    return sections


# 一行中的多个选项，形如 "A. xxx  B. yyy   C. zzz"
MULTI_OPT = re.compile(r"(?:^|\s)([A-E])\s*[\.．、:：]\s*")

def extract_opts(ln):
    """返回 [(字母, 内容), ...]，支持一行多选项"""
    matches = list(MULTI_OPT.finditer(ln))
    opts = []
    for i, m in enumerate(matches):
        letter = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(ln)
        content = ln[start:end].strip()
        opts.append((letter, content))
    return opts


def parse_choice(lines):
    """解析选择题：返回 [{no,stem,options}]"""
    items = []
    cur = None
    last_no = 0
    for ln in lines:
        ln = clean(ln)
        if not ln:
            continue
        m = QNUM.match(ln)
        # 题号必须严格递增且合理(1-200)才视为新题；否则可能是续行里的数字
        if m and 1 <= int(m.group(1)) <= 200 and int(m.group(1)) > last_no:
            no = int(m.group(1))
            last_no = no
            stem = ln[m.end():].strip()
            if cur:
                items.append(cur)
            cur = {"no": no, "stem": stem, "options": {}, "answer": None}
            continue
        # 提取该行选项
        opts = extract_opts(ln)
        if opts and cur:
            for letter, content in opts:
                if content:
                    cur["options"][letter] = content
            continue
        # 续行（题干换行）
        if cur and len(ln) > 1 and not re.match(r"^[A-E]\s*[\.．]", ln):
            cur["stem"] += ln
    if cur:
        items.append(cur)
    return [x for x in items if x["stem"] and len(x["options"]) >= 2]


def parse_simple(lines):
    """解析名词解释/问答/填空：返回 [{no,text}]，text 为题干或答案正文"""
    items = []
    cur = None
    for ln in lines:
        ln = clean(ln)
        if not ln:
            continue
        # 过滤页眉页脚
        if re.match(r"^第[一二三四五六七八九十百\d]+章", ln) and len(ln) < 30:
            continue
        if ln.isdigit() and len(ln) <= 4:
            continue
        m = QNUM.match(ln)
        if m:
            no = int(m.group(1))
            text = ln[m.end():].strip()
            if cur:
                items.append(cur)
            cur = {"no": no, "text": text}
        else:
            if cur and len(ln) > 1:
                cur["text"] += ln
    if cur:
        items.append(cur)
    return [x for x in items if x["text"]]


def parse_choice_answers(lines):
    """从答案区提取选择题答案 {no: 'ABCDE'...}"""
    ans = {}
    for ln in lines:
        ln = clean(ln)
        for m in ANS_CHOICE_INLINE.finditer(ln):
            ans[int(m.group(1))] = m.group(2).upper()
    return ans


def parse_book_text(text, book):
    """解析单本书全文文本。按『参考答案』切分章节块。"""
    # 去掉页码标记
    text = re.sub(r"<<<PAGE \d+>>>", "\n", text)
    lines = text.split("\n")
    # 找参考答案行索引
    marks = [i for i, ln in enumerate(lines) if ANSWER_TAIL.search(ln) and len(ln) < 30]
    results = []
    blocks = []
    prev = 0
    for mk in marks:
        blocks.append((prev, mk))  # (题目区,答案区起点)
        prev = mk
    if prev < len(lines):
        blocks.append((prev, len(lines)))

    for qstart, astart in blocks:
        # 题目区：从上个答案结束到本参考答案之前
        qregion = lines[qstart:astart]
        # 答案区：从参考答案到下一块起点
        aregion = lines[astart:] if astart != len(lines) else []
        if astart != len(lines):
            # 只取到下一 block 的题目起点(即下一个参考答案前的内容会混入,需截断)
            nxt = None
            for b in blocks:
                if b[0] > astart:
                    nxt = b[0]
                    break
            if nxt:
                aregion = lines[astart:nxt]

        qsec = split_sections(qregion)
        asec = split_sections(aregion)

        # 选择题
        q_choice = [l for t, l in qsec if t in ("choice",)]
        q_multi = [l for t, l in qsec if t == "multi"]
        a_choice = [l for t, l in asec if t in ("choice",)]
        a_multi = [l for t, l in asec if t == "multi"]
        # 若答案区未标注题型,整体当选择题答案行尝试
        if not a_choice and not a_multi:
            a_choice = [aregion]

        def answer_map(region_list):
            m = {}
            for ls in region_list:
                m.update(parse_choice_answers(ls))
            return m

        amap = answer_map(a_choice)
        mmap = answer_map(a_multi)

        for typ, qgroups, am in (("single", q_choice, amap), ("multi", q_multi, mmap)):
            for ls in qgroups:
                for q in parse_choice(ls):
                    ans = am.get(q["no"])
                    if ans:
                        q["answer"] = ans
                    q["type"] = typ
                    q["book"] = book
                    results.append(q)

        # 名词解释 / 问答 / 填空
        for typ in ("term", "qa", "blank"):
            qs = [l for t, l in qsec if t == typ]
            av = [l for t, l in asec if t == typ]
            # 若答案区无对应题型标记,跳过(避免错题配对)
            if not av:
                continue
            qitems = []
            for ls in qs:
                qitems += parse_simple(ls)
            aitems = []
            for ls in av:
                aitems += parse_simple(ls)
            amap2 = {x["no"]: x["text"] for x in aitems}
            for q in qitems:
                q["answer"] = amap2.get(q["no"], "")
                q["type"] = typ
                q["book"] = book
                if q["answer"]:
                    results.append(q)
    # 去重：同 book+type+stem
    seen = set()
    uniq = []
    for r in results:
        ident = r.get("stem") or r.get("text", "")
        key = (r["book"], r["type"], ident[:40])
        if key in seen:
            continue
        seen.add(key)
        # 选择题必须选项数>=3 且有答案
        if r["type"] in ("single", "multi"):
            if len(r.get("options", {})) < 3 or not r.get("answer"):
                continue
        uniq.append(r)
    return uniq


def main():
    allq = []
    for fn in os.listdir(TXT):
        if not fn.endswith(".txt"):
            continue
        book = fn[:-4]
        with open(os.path.join(TXT, fn), encoding="utf-8") as f:
            text = f.read()
        qs = parse_book_text(text, book)
        from collections import Counter
        c = Counter(x["type"] for x in qs)
        print(f"{book}: 共 {len(qs)} 题  {dict(c)}")
        allq += qs
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(allq, f, ensure_ascii=False, indent=1)
    print(f"合计 {len(allq)} 题 -> {OUT}")

if __name__ == "__main__":
    main()
