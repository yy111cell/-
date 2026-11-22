#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从康复评定 docx 中提取量表/评定内容，按条目组织成量表合集数据。"""
import os, re, json
from docx import Document

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(os.path.dirname(BASE), "知识点资料", "康复评定")
OUT = os.path.join(BASE, "data", "scales.json")

# 量表/评定主题关键词，用于给条目命名和分类
TOPIC_KW = [
    "Berg", "Brunnstrom", "Fugl", "Ashworth", "Barthel", "FIM", "MMSE", "GCS",
    "Borg", "PULSES", "Oswestry", "WHOQOL", "SIP", "NRS", "VDS", "FPS", "MMT",
    "平衡", "协调", "步态", "肌力", "肌张力", "关节活动度", "感觉功能", "疼痛",
    "日常生活活动", "心肺功能", "神经反射", "儿童", "生活质量", "并发症",
    "心功能", "痉挛", "偏瘫", "呼吸", "吞咽", "认知",
]

def para_text(p):
    return re.sub(r"\s+", " ", p.text).strip()

def looks_title(t):
    if not t or len(t) > 30:
        return False
    return bool(re.match(r"^[（(]?[一二三四五六七八九十\d]+[）)、.．]?\s*\S{2,20}$", t)
                or t.startswith(("（一）","（二）","（三）","①","②","③","1.","2.","3.")) )

def process(fn):
    d = Document(os.path.join(SRC, fn))
    paras = [para_text(p) for p in d.paragraphs]
    paras = [p for p in paras if p]
    if not paras:
        return []
    # 按"标题句"切分成条目：遇到标题则开新条目，否则并入当前
    items = []
    cur = {"title": paras[0][:30], "lines": [paras[0]]}
    for p in paras[1:]:
        if looks_title(p) and len(cur["lines"]) >= 1:
            items.append(cur)
            cur = {"title": p[:30], "lines": [p]}
        else:
            cur["lines"].append(p)
    items.append(cur)
    # 过滤太短、组装正文
    out = []
    for it in items:
        body = "\n".join(it["lines"])
        if len(body) < 40:
            continue
        # 从内容里找出主题标签
        topics = [k for k in TOPIC_KW if k.lower() in body.lower()]
        out.append({"title": it["title"], "body": body, "topics": topics, "source": fn})
    return out

def main():
    allitems = []
    for fn in sorted(os.listdir(SRC)):
        if not fn.endswith(".docx"):
            continue
        try:
            items = process(fn)
        except Exception as e:
            print("跳过", fn, e)
            continue
        print(f"{fn}: {len(items)} 条目")
        allitems += items
    # 只保留含主题关键词或与评定强相关的条目
    keep = [x for x in allitems if x["topics"] or any(k in x["body"] for k in ("评定","评分","分级","量表","指数"))]
    for i, x in enumerate(keep):
        x["id"] = f"s{i+1:03d}"
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(keep, f, ensure_ascii=False, indent=1)
    print(f"保留 {len(keep)} 个量表/评定条目 -> {OUT}")

if __name__ == "__main__":
    main()
