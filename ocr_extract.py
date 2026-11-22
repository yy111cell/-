#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫描件 PDF 全文 OCR，逐页保存文本，供后续题目解析使用。"""
import sys, os, time
import pymupdf
import numpy as np
from rapidocr_onnxruntime import RapidOCR

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(os.path.dirname(BASE), "习题资料")
OUT = os.path.join(BASE, "data", "ocr")
os.makedirs(OUT, exist_ok=True)

SCANNED = {
    "系统解剖学": "06.系统解剖学习题集-第3版.pdf",
    "儿童康复学": "儿童康复学学习指导及习题集.pdf",
    "康复功能评定学": "康复功能评定学学习指导及习题集 第2版.pdf",
    "神经康复学": "神经康复学学习指导及习题集  第3版_14531526.pdf",
    "肌肉解剖学": "肌肉骨骼康复学学习指导及习题集 第3版.pdf",
}

ocr = RapidOCR()
subject = sys.argv[1]
fname = SCANNED[subject]
pdf = os.path.join(SRC, fname)
d = pymupdf.open(pdf)
outdir = os.path.join(OUT, subject)
os.makedirs(outdir, exist_ok=True)
# 可选页码范围: argv[2]=起始 argv[3]=结束
p_start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
p_end = int(sys.argv[3]) if len(sys.argv) > 3 else d.page_count
t0 = time.time()
print(f"[{subject}] 开始 OCR，页 {p_start}-{p_end}，共 {d.page_count} 页", flush=True)
for i in range(p_start, min(p_end, d.page_count)):
    fp = os.path.join(outdir, f"p{i:04d}.txt")
    if os.path.exists(fp):
        continue
    zoom = float(os.environ.get("OCR_ZOOM", "1.7"))
    pix = d[i].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), colorspace=pymupdf.csGRAY)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
    res, _ = ocr(img)
    lines = [x[1] for x in res] if res else []
    with open(fp, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    if (i + 1) % 25 == 0:
        print(f"[{subject}] {i+1}/{d.page_count} 用时 {time.time()-t0:.0f}s", flush=True)
print(f"[{subject}] 完成，用时 {time.time()-t0:.0f}s", flush=True)
