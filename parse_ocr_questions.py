#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解析 OCR 文本（扫描件），复用通用解析器，输出 questions_ocr.json。"""
import os, re, json, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_questions import parse_book_text

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OCR = os.path.join(BASE, "data", "ocr")
OUT = os.path.join(BASE, "data", "questions_ocr.json")

def merge_pages(subject):
    folder = os.path.join(OCR, subject)
    if not os.path.isdir(folder):
        return ""
    pages = sorted(f for f in os.listdir(folder) if f.endswith(".txt"))
    parts = []
    for p in pages:
        with open(os.path.join(folder, p), encoding="utf-8") as f:
            txt = f.read()
        # 剔除目录页：题型标记密集但每行多为纯页码（目录特征）
        lines = txt.split("\n")
        digit_lines = sum(1 for l in lines if l.strip().isdigit() and len(l.strip())<=4)
        if digit_lines >= 12:   # 目录页含大量页码
            continue
        parts.append("\n<<<PAGE %s>>>\n" % p[1:5] + txt)
    return "\n".join(parts)

def main():
    subjects = ["系统解剖学","儿童康复学","肌肉解剖学","康复功能评定学","神经康复学"]
    allq = []
    for s in subjects:
        text = merge_pages(s)
        if not text:
            print(s, "无OCR文本，跳过")
            continue
        qs = parse_book_text(text, s)
        for q in qs:
            q["subject"] = s
        from collections import Counter
        c = Counter(q["type"] for q in qs)
        print(f"{s}: {len(qs)} 题 {dict(c)}")
        allq += qs
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(allq, f, ensure_ascii=False, indent=1)
    print(f"合计 {len(allq)} -> {OUT}")

if __name__ == "__main__":
    main()
