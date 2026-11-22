#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把解剖文档的文字序列切分成肌肉卡片，关联图片，输出结构化数据。"""
import os, re, json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEQ = os.path.join(BASE, "data", "muscle_seq.json")
OUT = os.path.join(BASE, "data", "muscles.json")

# 神经支配补充（解剖学常识，供学习参考）——资料中缺失，作为增值标注
NERVE = {
    "胸锁乳突肌":"副神经、颈2-3", "斜方肌":"副神经", "菱形肌":"肩胛背神经",
    "肩胛提肌":"肩胛背神经", "前锯肌":"胸长神经", "胸小肌":"胸内侧神经",
    "胸大肌":"胸内、外侧神经", "背阔肌":"胸背神经", "冈下肌":"肩胛上神经",
    "冈上肌":"肩胛上神经", "小圆肌":"腋神经", "大圆肌":"肩胛下神经",
    "三角肌":"腋神经", "肱二头肌":"肌皮神经", "肱三头肌":"桡神经",
    "喙肱肌":"肌皮神经", "肱肌":"肌皮神经", "肱桡肌":"桡神经",
    "腹直肌":"肋间神经", "腹外斜肌":"肋间神经、髂腹下神经", "腹内斜肌":"肋间神经",
    "腹横肌":"肋间神经", "膈肌":"膈神经", "竖脊肌":"脊神经后支",
    "腰方肌":"腰神经前支", "梨状肌":"骶丛分支", "臀大肌":"臀下神经",
    "臀中肌":"臀上神经", "臀小肌":"臀上神经", "髂腰肌":"腰丛、股神经",
    "股四头肌":"股神经", "缝匠肌":"股神经", "股二头肌":"坐骨神经",
    "半腱肌":"坐骨神经", "半膜肌":"坐骨神经", "小腿三头肌":"胫神经",
    "胫骨前肌":"腓深神经", "腓肠肌":"胫神经", "比目鱼肌":"胫神经",
}

# 标题行：以 · 开头且以：结尾，或纯肌肉名+：，或"数字⁰描述"分类行
MUSCLE_TITLE = re.compile(r"^[·•]?\s*([\u4e00-\u9fa5A-Za-z]{2,12}(?:肌|腱膜|韧带))\s*[:：]\s*$")
GROUP_LINE = re.compile(r"^\d+[⁰0-9⁰]\s*(使|运动|位于|作用|组成)|^[①②③④⑤⑥⑦]")
NOISE = re.compile(r"^\d{6,}|^[-\d]{6,}$")

def clean(t):
    t = re.sub(r"^\d{5,}\s*", "", t)   # 去掉图片编号串
    t = re.sub(r"\s+", " ", t).strip()
    return t

def is_field(t):
    return re.match(r"^(起|止|作用|近固定|远固定|位置|结构|运动|功能|下固定|上固定)\s*[:：]", t)

def build_for_doc(doc):
    seq = doc["seq"]
    cards = []
    cur = None
    def flush():
        nonlocal cur
        if cur and len(cur["detail"]) >= 1:
            detail = cur["detail"]
            # 把所有行拼成一段，用字段标记切分（支持同一行含多个字段）
            blob = " ".join(detail)
            fields = list(re.finditer(r"(起|止|作用|近固定|远固定|位置|结构|运动|功能|下固定|上固定)\s*[:：]", blob))
            fmap = {}
            for i, fm in enumerate(fields):
                k = fm.group(1)
                start = fm.end()
                end = fields[i+1].start() if i+1 < len(fields) else len(blob)
                val = blob[start:end].strip()
                fmap.setdefault(k, []).append(val)
            origin = " ".join(fmap.get("起", []))
            insert = " ".join(fmap.get("止", []))
            action = []
            for k in ("作用","功能","近固定","远固定","下固定","上固定","运动"):
                if k in fmap:
                    action.append(k + "：" + " ".join(fmap[k]))
            cur["origin"] = clean(origin)[:160]
            cur["insertion"] = clean(insert)[:160]
            cur["action"] = "；".join(action)[:300]
            cur.pop("detail")
            if cur["origin"] or cur["action"]:
                cards.append(cur)
    for x in seq:
        if x["kind"] == "image":
            if cur:
                cur["imgs_tmp"].append(x.get("local"))
            continue
        t = clean(x["text"])
        if not t or NOISE.match(t):
            continue
        m = MUSCLE_TITLE.match(t)
        if m and not GROUP_LINE.match(t):
            flush()
            name = m.group(1)
            cur = {"name": name, "detail": [], "image": None, "imgs_tmp": [],
                   "nerve": NERVE.get(name, ""), "source": doc["doc"]}
            continue
        if cur:
            # 遇到新的分类行，结束当前肌肉
            if GROUP_LINE.match(t) and not is_field(t) and not re.match(r"^\d+[\.．]", t):
                flush(); cur = None
                continue
            if is_field(t) or re.match(r"^\d+[\.．]", t) or len(t) > 3:
                cur["detail"].append(t)
    flush()
    # 关联图片：按文档内出现顺序，将图片池与肌肉卡按顺序一一配对（提升配图多样性）
    docimgs = [x.get("local") for x in seq if x["kind"] == "image" and x.get("local")]
    for c in cards:
        c.pop("imgs_tmp", None)
    for i, c in enumerate(cards):
        if i < len(docimgs):
            c["image"] = docimgs[i]
    return cards

def main():
    docs = json.load(open(SEQ, encoding="utf-8"))
    allcards = []
    for d in docs:
        cards = build_for_doc(d)
        print(f"{d['doc']}: {len(cards)} 块肌肉")
        allcards += cards
    # 去重：同名保留信息最全的
    seen = {}
    for c in allcards:
        k = c["name"]
        score = len(c["origin"]) + len(c["action"])
        if k not in seen or score > seen[k][0]:
            seen[k] = (score, c)
    final = [v[1] for v in seen.values()]
    # 过滤过短
    final = [c for c in final if len(c["origin"]) + len(c["action"]) >= 8]
    # 过滤非肌肉条目（骨、韧带、椎间盘、终板、关节等结构不是单块肌肉）
    NON_MUSCLE = ["椎间盘","终板","软骨终板","骨性终板","纤维环","髓核","关节囊","韧带",
                  "椎骨","胸骨","肋骨","锁骨","肩胛骨","肱骨","股骨","髂骨","脊柱","颅骨",
                  "颞下颌关节","肩关节","肘关节","髋关节","膝关节","踝关节","骨盆"]
    def is_muscle(c):
        n = c["name"]
        if "肌" not in n:
            return False
        if any(x in n for x in ["关节","韧带","椎间盘","终板","骨","软骨"]):
            return False
        return True
    final = [c for c in final if is_muscle(c)]
    # 分配 id
    for i, c in enumerate(final):
        c["id"] = f"m{i+1:03d}"
    # 图片路径前缀处理
    for c in final:
        if c["image"]:
            c["image"] = c["image"].replace("images/muscle/", "images/muscle/")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=1)
    print(f"去重后 {len(final)} 块肌肉 -> {OUT}")
    withimg = sum(1 for c in final if c["image"])
    print(f"其中有图片 {withimg} 块")

if __name__ == "__main__":
    main()
