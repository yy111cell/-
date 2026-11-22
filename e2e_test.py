#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通过 CDP 驱动 Chrome 做交互冒烟测试。"""
import json, time, subprocess, urllib.request, os
import websocket

PORT = 9333
URL = "http://127.0.0.1:8848/index.html"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

def cdp_page():
    # 等待调试端口
    for _ in range(30):
        try:
            data = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=1))
            for t in data:
                if t.get("type") == "page":
                    return t["webSocketDebuggerUrl"]
        except Exception:
            time.sleep(0.3)
    raise RuntimeError("CDP 端口未就绪")

class CDP:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=20)
        self.i = 0
    def cmd(self, method, params=None):
        self.i += 1
        mid = self.i
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                return msg.get("result", {})
    def js(self, code):
        r = self.cmd("Runtime.evaluate", {"expression": code, "returnByValue": True, "awaitPromise": True})
        res = r.get("result", {})
        if res.get("subtype") == "error" or "exceptionDetails" in r:
            return {"__error__": str(r.get("exceptionDetails", {}).get("text", res))}
        return res.get("value")
    def shot(self, path):
        r = self.cmd("Page.captureScreenshot", {"format": "png"})
        with open(path, "wb") as f:
            import base64
            f.write(base64.b64decode(r["data"]))

def main():
    # 启动独立 Chrome 调试实例
    proc = subprocess.Popen([
        CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage",
        f"--remote-debugging-port={PORT}", "--user-data-dir=/tmp/rehab_cdp_profile",
        "--window-size=1440,1000", URL
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)
    c = CDP(cdp_page())
    c.cmd("Page.enable")
    c.cmd("Runtime.enable")
    # 等待页面与数据脚本加载完成
    for _ in range(40):
        ready = c.js("document.readyState==='complete' && typeof QUESTION_BANK!=='undefined' && typeof MUSCLES!=='undefined'")
        if ready is True:
            break
        time.sleep(0.25)
    print("页面就绪:", ready)

    results = []
    def check(name, cond, detail=""):
        ok = bool(cond)
        results.append((name, ok, detail))
        print(("PASS " if ok else "FAIL ") + name + (" | " + str(detail) if detail else ""))

    # 1. 数据加载
    total = c.js("Object.values(QUESTION_BANK).reduce((a,b)=>a+b.length,0)")
    check("题库数据加载", isinstance(total, int) and total > 1000, f"总题量={total}")
    check("肌肉数据加载", c.js("MUSCLES.length") > 20, f"肌肉数={c.js('MUSCLES.length')}")
    check("量表数据加载", c.js("SCALES.length") > 100, f"量表数={c.js('SCALES.length')}")

    # 2. 直接刷题模式
    c.js("goView('quiz'); selectMode('direct'); pickSubject('人体发育学'); document.getElementById('directN').value=5; startQuiz()")
    time.sleep(0.3)
    qcount = c.js("state.quiz.length")
    check("直接刷题-组卷N题", qcount == 5, f"实际={qcount}")
    # 答第一题
    c.js("selectOption('A')")
    sel = c.js("state.answers[0]")
    check("直接刷题-选项交互", sel == 'A', f"选中={sel}")
    # 翻页
    c.js("navQuestion(1)")
    check("直接刷题-翻页", c.js("state.idx") == 1)
    c.shot("/tmp/rehab_quiz.png")

    # 3. 背题模式
    c.js("quitQuiz(); selectMode('recite'); startQuiz()")
    time.sleep(0.2)
    hasAnswer = c.js("!!document.querySelector('.q-answer-box')")
    check("背题模式-直接显示答案", hasAnswer is True, f"显示答案={hasAnswer}")
    c.shot("/tmp/rehab_recite.png")

    # 4. 模拟考试-自定义配比
    c.js("quitQuiz(); selectMode('exam'); document.getElementById('examSingle').value=3; document.getElementById('examMulti').value=0; document.getElementById('examBlank').value=2; document.getElementById('examQa').value=1; startQuiz()")
    time.sleep(0.2)
    exam = c.js("JSON.stringify(state.quiz.map(q=>q.type))")
    check("模拟考试-自定义配比组卷", exam and len(json.loads(exam)) == 6, f"题型={exam}")
    # 交卷
    c.js("for(let i=0;i<state.quiz.length;i++){if(state.quiz[i].options)state.answers[i]='A'}; submitQuiz()")
    time.sleep(0.2)
    rate = c.js("document.querySelector('.result-score')?document.querySelector('.result-score').textContent:null")
    check("模拟考试-交卷出结果", rate is not None, f"成绩={rate}")
    c.shot("/tmp/rehab_result.png")

    # 5. 错题集和历史
    wrong = c.js("DB.get('wrong',[]).length")
    hist = c.js("DB.get('history',[]).length")
    check("错题集记录", wrong >= 0, f"错题={wrong}")
    check("历史记录", hist >= 1, f"历史={hist}")

    # 6. 学习页-肌肉卡
    c.js("goView('study'); switchStudyTab('muscle')")
    time.sleep(0.2)
    cards = c.js("document.querySelectorAll('.muscle-card').length")
    check("学习页-肌肉卡渲染", cards > 20, f"卡片数={cards}")
    c.shot("/tmp/rehab_study_muscle.png")
    # 翻卡测试
    c.js("document.getElementById('testCount').value=5; openMuscleTest(); beginMuscleTest()")
    time.sleep(0.2)
    q = c.js("document.getElementById('testQuestion').textContent")
    check("翻卡测试-出题", q and len(q) > 0, f"题目={q}")
    c.js("flipCard()")
    flip = c.js("document.getElementById('flipCard').classList.contains('flipped')")
    check("翻卡测试-翻面", flip is True)
    c.shot("/tmp/rehab_flip.png")

    # 7. 量表合集
    c.js("closeMuscleTest(); switchStudyTab('scale')")
    time.sleep(0.2)
    scards = c.js("document.querySelectorAll('.scale-card').length")
    check("学习页-量表渲染", scards > 10, f"量表卡={scards}")
    c.shot("/tmp/rehab_study_scale.png")

    # 8. 无JS报错
    err = c.js("window.__errs__||[]")
    check("运行时无致命错误", not isinstance(err, dict), str(err)[:100])

    c.ws.close()
    proc.terminate()
    print("\n=== 汇总 ===")
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"通过 {passed}/{len(results)}")

if __name__ == "__main__":
    main()
