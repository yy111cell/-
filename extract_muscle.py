#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从解剖 docx 中按文档顺序提取 [段落文字 / 图片]，并导出图片文件。"""
import os, zipfile, shutil, re
from lxml import etree

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(os.path.dirname(BASE), "知识点资料")
IMG_OUT = os.path.join(BASE, "images", "muscle")
DATA_OUT = os.path.join(BASE, "data", "muscle_seq.json")
os.makedirs(IMG_OUT, exist_ok=True)

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "v": "urn:schemas-microsoft-com:vml",
}

DOCS = [
    "全身 主要骨的连结及肌肉  上肢.docx",
    "全身主要骨.docx",
    "全身主要骨连结级肌肉.docx",
]

def rid_map(z):
    rels = etree.fromstring(z.read("word/_rels/document.xml.rels"))
    m = {}
    for r in rels:
        if r.get("Type", "").endswith("/image"):
            m[r.get("Id")] = r.get("Target")
    return m

def para_text(p):
    return "".join(p.itertext()).strip()

def para_images(p, rmap, prefix):
    imgs = []
    # DrawingML blips
    for blip in p.findall(".//a:blip", NS):
        rid = blip.get("{%s}embed" % NS["r"])
        if rid in rmap:
            imgs.append(rmap[rid])
    # VML imagedata
    for im in p.findall(".//v:imagedata", NS):
        rid = im.get("{%s}id" % NS["r"])
        if rid in rmap:
            imgs.append(rmap[rid])
    return imgs

def process(docname):
    path = os.path.join(SRC, docname)
    z = zipfile.ZipFile(path)
    rmap = rid_map(z)
    root = etree.fromstring(z.read("word/document.xml"))
    body = root.find("w:body", NS)
    seq = []
    tag_short = docname.replace(".docx", "").replace(" ", "")[:6]
    for el in body:
        if el.tag.endswith("}p"):
            txt = para_text(el)
            imgs = para_images(el, rmap, tag_short)
            for im in imgs:
                seq.append({"kind": "image", "src": im})
            if txt:
                seq.append({"kind": "text", "text": txt})
        elif el.tag.endswith("}tbl"):
            # 表格内文字与图片
            for p in el.findall(".//w:p", NS):
                txt = para_text(p)
                imgs = para_images(p, rmap, tag_short)
                for im in imgs:
                    seq.append({"kind": "image", "src": im})
                if txt:
                    seq.append({"kind": "text", "text": txt})
    # 导出图片
    for item in seq:
        if item["kind"] == "image":
            src = item["src"].replace("\\", "/")
            zpath = "word/" + src if not src.startswith("word/") else src
            if zpath not in z.namelist():
                continue
            fname = tag_short + "_" + os.path.basename(src)
            out = os.path.join(IMG_OUT, fname)
            with z.open(zpath) as fsrc, open(out, "wb") as fdst:
                shutil.copyfileobj(fsrc, fdst)
            item["local"] = "images/muscle/" + fname
    z.close()
    return {"doc": docname, "seq": seq}

def main():
    result = []
    for d in DOCS:
        r = process(d)
        nimg = sum(1 for x in r["seq"] if x["kind"] == "image")
        ntext = sum(1 for x in r["seq"] if x["kind"] == "text")
        print(f"{d}: 图片 {nimg} 段文字 {ntext}")
        result.append(r)
    with open(DATA_OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print("序列已保存", DATA_OUT)

if __name__ == "__main__":
    import json
    main()
