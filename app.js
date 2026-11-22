/* ============================================================
   康复君 · 交互逻辑
   ============================================================ */
'use strict';

const SUBJECTS = ["系统解剖学","儿童康复学","肌肉解剖学","康复功能评定学",
                  "人体发育学","神经康复学","物理治疗学","语言治疗学","作业治疗学"];
const MODE_NAME = {direct:"直接刷题", recite:"背题模式", exam:"模拟考试"};

// ---------- 本地存储 ----------
const DB = {
  get(k, d){ try{ const v=localStorage.getItem('rk_'+k); return v?JSON.parse(v):d; }catch(e){ return d; } },
  set(k, v){ try{ localStorage.setItem('rk_'+k, JSON.stringify(v)); }catch(e){} }
};

let state = {
  view:'home', subject:'人体发育学', mode:'direct',
  quiz:[], idx:0, answers:{}, submitted:false,
  testCards:[], testIdx:0, testFlipped:false,
  scaleTopic:'全部'
};

// ---------- 工具 ----------
function $(id){ return document.getElementById(id); }
function shuffle(arr){ const a=[...arr]; for(let i=a.length-1;i>0;i--){ const j=Math.floor(Math.random()*(i+1)); [a[i],a[j]]=[a[j],a[i]]; } return a; }
function toast(msg){ const t=$('toast'); t.textContent=msg; t.classList.add('show'); clearTimeout(t._t); t._t=setTimeout(()=>t.classList.remove('show'),2200); }
function esc(s){ return String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function subjCount(s){ return (QUESTION_BANK[s]||[]).length; }
function cleanTail(s){ return String(s||'').replace(/\s*\d+[\.．]$/,'').replace(/\s*\d+[⁰]\s*使.*$/,'').trim(); }

// ---------- 视图导航 ----------
function goView(v){
  state.view=v;
  document.querySelectorAll('.view').forEach(el=>el.classList.toggle('active', el.id==='view-'+v));
  document.querySelectorAll('.nav-item').forEach(el=>el.classList.toggle('active', el.dataset.view===v || (v==='records'&&el.dataset.view==='quiz')));
  if(v==='home') renderHome();
  if(v==='quiz') renderSetup();
  if(v==='study'){ renderMuscles(); renderScales(); }
  if(v==='records') renderRecords();
  window.scrollTo({top:0,behavior:'smooth'});
}
function quickStart(mode){
  goView('quiz'); selectMode(mode);
  toast('已选择 '+MODE_NAME[mode]+'，确认科目后点击开始');
}

// ---------- 首页 ----------
function renderHome(){
  const bank=QUESTION_BANK;
  const total=Object.values(bank).reduce((a,b)=>a+b.length,0);
  const rec=DB.get('history',[]);
  const wrong=DB.get('wrong',[]);
  $('heroMetrics').innerHTML=`
    <div class="metric"><b>${total.toLocaleString()}</b><span>优质题目</span></div>
    <div class="metric"><b>9</b><span>核心科目</span></div>
    <div class="metric"><b>${MUSCLES.length}</b><span>肌肉记忆卡</span></div>
    <div class="metric"><b>${SCALES.length}</b><span>量表条目</span></div>`;
  $('homeSubjects').innerHTML=SUBJECTS.map((s,i)=>`
    <div class="subject-tile" onclick="pickSubjectHome('${s}')">
      <span class="s-num">${String(i+1).padStart(2,'0')}</span>
      <span class="s-name">${s}</span>
      <span class="s-count ${subjCount(s)===0?'zero':''}">${subjCount(s)} 题</span>
    </div>`).join('');
  $('topMastered').textContent='✦ '+rec.reduce((a,h)=>a+(h.correct||0),0);
}
function pickSubjectHome(s){ state.subject=s; goView('quiz'); renderSetup(); }

// ---------- 刷题配置 ----------
function renderSetup(){
  $('quizSubjectChips').innerHTML=SUBJECTS.map(s=>`
    <button class="chip ${s===state.subject?'active':''}" onclick="pickSubject('${s}')">${s}<span class="n">${subjCount(s)}</span></button>`).join('');
  const tip=subjCount(state.subject)===0?'⚠ 该科目题库整理中，可先练习其他科目':`本科目共 ${subjCount(state.subject)} 题`;
  $('setupTip').textContent=tip;
  updateExamHint();
}
function pickSubject(s){ state.subject=s; renderSetup(); }
function setN(n){ $('directN').value=n; }
function selectMode(m){
  state.mode=m;
  document.querySelectorAll('.mode-tab').forEach(el=>el.classList.toggle('active',el.dataset.mode===m));
  $('cfg-direct').style.display = m==='direct'?'block':'none';
  $('cfg-recite').style.display = m==='recite'?'block':'none';
  $('cfg-exam').style.display   = m==='exam'?'block':'none';
}
function resetExamDefault(){ $('examSingle').value=30; $('examMulti').value=0; $('examBlank').value=5; $('examQa').value=5; updateExamHint(); }
function updateExamHint(){}

function getCheckedTypes(containerId){
  return [...$(containerId).querySelectorAll('input:checked')].map(x=>x.value);
}

function startQuiz(){
  const bank=QUESTION_BANK[state.subject]||[];
  if(!bank.length){ toast('该科目题库整理中，请选其他科目'); return; }
  let picked=[];
  if(state.mode==='direct'){
    const n=Math.max(1,Math.min(200,parseInt($('directN').value)||20));
    let types=getCheckedTypes('directTypes');
    let pool=bank.filter(q=>types.includes(q.type));
    // 若所选题型无题，自动扩展到该科所有可用题型
    if(!pool.length){
      const avail=[...new Set(bank.map(q=>q.type))];
      pool=bank.filter(q=>avail.includes(q.type));
      if(pool.length) toast('所选题型本科目暂无，已自动使用全部可用题型');
    }
    if(!pool.length){ toast('该科目题库整理中'); return; }
    picked=shuffle(pool).slice(0,n);
  } else if(state.mode==='recite'){
    let types=getCheckedTypes('reciteTypes');
    let pool=bank.filter(q=>types.includes(q.type));
    if(!pool.length){
      const avail=[...new Set(bank.map(q=>q.type))];
      pool=bank.filter(q=>avail.includes(q.type));
    }
    if(!pool.length){ toast('该科目题库整理中'); return; }
    picked=shuffle(pool).slice(0,Math.min(pool.length,50));
  } else {
    const spec={single:parseInt($('examSingle').value)||0, multi:parseInt($('examMulti').value)||0,
                blank:parseInt($('examBlank').value)||0, qa:parseInt($('examQa').value)||0};
    const total=Object.values(spec).reduce((a,b)=>a+b,0);
    if(!total){ toast('请设置至少一道题'); return; }
    for(const [t,n] of Object.entries(spec)){
      const pool=bank.filter(q=>q.type===t);
      picked=picked.concat(shuffle(pool).slice(0,Math.min(n,pool.length)));
    }
    // 若实际组卷不足目标数，用全科随机补足
    if(picked.length<total){
      const used=new Set(picked.map(q=>q.stem));
      const rest=shuffle(bank.filter(q=>!used.has(q.stem))).slice(0,total-picked.length);
      picked=picked.concat(rest);
    }
    if(!picked.length){ toast('该科目暂无符合配比的题目'); return; }
  }
  state.quiz=picked; state.idx=0; state.answers={}; state.submitted=false;
  $('quizSetup').style.display='none';
  $('quizArea').style.display='block';
  $('resultArea').style.display='none';
  renderQuestion();
}

function quitQuiz(){
  $('quizArea').style.display='none'; $('resultArea').style.display='none'; $('quizSetup').style.display='block';
  state.quiz=[];
}

// ---------- 渲染单题 ----------
function renderQuestion(){
  const q=state.quiz[state.idx];
  if(!q) return;
  const isRecite=state.mode==='recite';
  const total=state.quiz.length;
  $('quizSubjectLabel').textContent=state.subject;
  $('quizModeLabel').textContent=MODE_NAME[state.mode];
  $('quizProgressText').textContent=(state.idx+1)+'/'+total;
  $('quizProgressBar').style.width=((state.idx+1)/total*100)+'%';

  const typeLabel={single:'单选题',multi:'多选题',blank:'填空 / 名词解释',qa:'问答题'}[q.type]||'题目';
  let html=`<div class="q-card"><span class="q-type ${['qa','blank'].includes(q.type)?'qa':''}">${typeLabel}${isRecite?'<span class="recite-badge">背题模式 · 直接看解析</span>':''}</span>`;
  html+=`<div class="q-stem"><span class="qno">${state.idx+1}.</span>${esc(q.stem)}</div>`;

  if(q.type==='single'||q.type==='multi'){
    html+='<div class="q-options">';
    q.options.forEach((op,i)=>{
      const key='ABCDE'[i];
      let cls='q-option';
      const picked=state.answers[state.idx];
      if(isRecite||state.submitted){
        if(isAnswerCorrect(q,key)) cls+=' correct';
        else if(picked&&picked.includes(key)) cls+=' wrong';
      } else if(picked&&picked.includes(key)) cls+=' selected';
      const multi=q.type==='multi'?'□ ':'';
      html+=`<div class="${cls}" onclick="${(isRecite||state.submitted)?'':`selectOption('${key}')`}">
        <span class="opt-key">${key}</span><span>${multi}${esc(op)}</span></div>`;
    });
    html+='</div>';
    if(isRecite||state.submitted){
      html+=answerBox(q);
    }
  } else {
    // 填空/问答：作答框
    if(isRecite||state.submitted){
      html+=`<div class="q-answer-box"><div class="lbl">参考答案</div>${esc(q.answer||'（资料中未提供标准答案）')}</div>`;
    } else {
      html+=`<textarea class="q-input" id="textAnswer" placeholder="在此作答（选做，交卷后可对照参考答案）">${esc(state.answers[state.idx]||'')}</textarea>`;
    }
  }
  html+='</div>';
  $('questionContainer').innerHTML=html;

  // 底部按钮
  $('btnPrevQ').style.display=state.idx>0?'inline-flex':'none';
  const isLast=state.idx===state.quiz.length-1;
  if(isRecite){
    $('btnNextQ').style.display=state.idx<state.quiz.length-1?'inline-flex':'none';
    $('btnSubmitQuiz').style.display='none';
  } else {
    $('btnNextQ').style.display=isLast?'none':'inline-flex';
    $('btnSubmitQuiz').style.display=isLast?'inline-flex':'none';
  }
}

function answerBox(q){
  const ans=q.answer||'';
  return `<div class="q-answer-box"><div class="lbl">正确答案：${esc(ans)}</div>
    ${q.analysis?'<p>'+esc(q.analysis)+'</p>':''}
    <p style="color:var(--ink-mute);font-size:12px;margin-top:8px">${q.type==='multi'?'（多选，答案可能含多个字母）':'解析由题库资料整理'}</p></div>`;
}

function isAnswerCorrect(q,key){ return (q.answer||'').toUpperCase().includes(key.toUpperCase()); }

function selectOption(key){
  const q=state.quiz[state.idx];
  let cur=state.answers[state.idx]||'';
  if(q.type==='single'){ cur=key; }
  else {
    if(cur.includes(key)) cur=cur.replace(key,'');
    else cur+=key;
    cur=cur.split('').sort().join('');
  }
  state.answers[state.idx]=cur;
  renderQuestion();
}

function navQuestion(d){
  // 保存填空/问答输入
  const ta=$('textAnswer'); if(ta) state.answers[state.idx]=ta.value;
  const ni=state.idx+d;
  if(ni<0||ni>=state.quiz.length) return;
  state.idx=ni; renderQuestion();
}

// ---------- 交卷与结果 ----------
function submitQuiz(){
  const ta=$('textAnswer'); if(ta) state.answers[state.idx]=ta.value;
  state.submitted=true;
  // 判分（选择/多选）
  let correct=0, judged=0;
  const review=[];
  state.quiz.forEach((q,i)=>{
    if(q.type==='single'||q.type==='multi'){
      judged++;
      const ua=(state.answers[i]||'').toUpperCase().split('').sort().join('');
      const ca=(q.answer||'').toUpperCase().replace(/[^A-E]/g,'').split('').sort().join('');
      const ok=ua===ca && ua.length>0;
      if(ok) correct++;
      review.push({q,ok,ua,ca});
      // 错题集
      if(!ok) addWrong(q);
    }
  });
  const rate=judged?Math.round(correct/judged*100):0;
  // 历史记录
  const hist=DB.get('history',[]);
  hist.unshift({date:new Date().toLocaleString('zh-CN'),subject:state.subject,mode:state.mode,
                total:state.quiz.length,judged,correct,rate});
  DB.set('history',hist.slice(0,100));

  // 结果页
  $('quizArea').style.display='none';
  const r=$('resultArea'); r.style.display='block';
  const fill=state.quiz.length-judged;
  r.innerHTML=`
    <div class="result-score">${rate}<small>%</small></div>
    <p class="result-label">${state.subject} · ${MODE_NAME[state.mode]} 正确率</p>
    <div class="result-stats">
      <div><b>${state.quiz.length}</b><span>总题数</span></div>
      <div><b>${correct}</b><span>答对</span></div>
      <div><b>${judged-correct}</b><span>答错</span></div>
      <div><b>${fill}</b><span>${fill?'填空/问答(自评)':'—'}</span></div>
    </div>
    <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap">
      <button class="btn btn-primary" onclick="restartSame()">再来一组</button>
      <button class="btn btn-ghost" style="border-color:var(--line);color:var(--ink-soft)" onclick="goView('records')">看错题 →</button>
      <button class="btn btn-ghost" style="border-color:var(--line);color:var(--ink-soft)" onclick="quitQuiz()">返回配置</button>
    </div>
    <div class="result-review">
      <h3 style="font-family:var(--serif);margin:26px 0 8px">答题回顾</h3>
      ${review.map((x,i)=>`<div class="review-item">
        <h4><span class="rv-tag ${x.ok?'rv-ok':'rv-no'}">${x.ok?'✓ 正确':'✕ 错误'}</span>${esc(x.q.stem)}</h4>
        <p>你的答案：${esc(x.ua||'未答')}　正确答案：${esc(x.ca)}</p></div>`).join('')}
      ${state.quiz.filter(q=>!['single','multi'].includes(q.type)).map(q=>`
        <div class="review-item"><h4><span class="rv-tag rv-ok">参考答案</span>${esc(q.stem)}</h4>
        <p>${esc(q.answer||'—')}</p></div>`).join('')}
    </div>`;
  renderHome();
}
function restartSame(){ $('resultArea').style.display='none'; $('quizArea').style.display='block'; startQuiz(); }

// ---------- 错题集 ----------
function addWrong(q){
  let w=DB.get('wrong',[]);
  const key=(q.stem||'').slice(0,50);
  const ex=w.find(x=>x.key===key);
  if(ex){ ex.times=(ex.times||1)+1; ex.last=new Date().toLocaleString('zh-CN'); }
  else w.unshift({key,stem:q.stem,type:q.type,options:q.options||[],answer:q.answer,subject:state.subject,times:1,last:new Date().toLocaleString('zh-CN')});
  DB.set('wrong',w);
}
function renderRecords(){
  const wrong=DB.get('wrong',[]), hist=DB.get('history',[]);
  $('wrongBadge').textContent=wrong.length;
  $('wrongList').innerHTML = wrong.length ? wrong.map((w,i)=>`
    <div class="wrong-item">
      <h4>${i+1}. ${esc(w.stem)}</h4>
      <div class="w-ans">正确答案：<b>${esc(w.answer||'—')}</b>　·　${esc(w.subject)}　·　错误 ${w.times} 次</div>
      ${w.options&&w.options.length?'<div class="w-ans" style="margin-top:8px;color:var(--ink-mute)">'+w.options.map((o,j)=>'ABCDE'[j]+'. '+esc(o)).join('　')+'</div>':''}
      <div style="margin-top:10px"><button class="mini-btn" onclick="removeWrong(${i})">移除</button></div>
    </div>`).join('') : `<div class="empty-state"><div class="em-ico">✦</div><p>暂无错题，继续保持！</p></div>`;
  $('historyList').innerHTML = hist.length ? hist.map(h=>`
    <div class="hist-item">
      <span class="h-date">${esc(h.date)}</span>
      <span class="h-subj">${esc(h.subject)}</span>
      <span class="h-mode">${MODE_NAME[h.mode]||''}</span>
      <span style="font-size:12px;color:var(--ink-mute)">${h.correct}/${h.judged||0} 正确</span>
      <span class="h-score">${h.rate}%</span>
    </div>`).join('') : `<div class="empty-state"><div class="em-ico">◷</div><p>还没有练习记录，去刷题吧！</p></div>`;
}
function removeWrong(i){ const w=DB.get('wrong',[]); w.splice(i,1); DB.set('wrong',w); renderRecords(); }
function clearRecords(){
  if(!confirm('确定清空全部错题与历史记录吗？')) return;
  DB.set('wrong',[]); DB.set('history',[]); renderRecords(); renderHome(); toast('记录已清空');
}
function switchRecordTab(t){
  document.querySelectorAll('[data-rtab]').forEach(el=>el.classList.toggle('active',el.dataset.rtab===t));
  $('record-wrong').style.display=t==='wrong'?'block':'none';
  $('record-history').style.display=t==='history'?'block':'none';
}

// ---------- 学习页：肌肉卡 ----------
function switchStudyTab(t){
  document.querySelectorAll('[data-tab]').forEach(el=>el.classList.toggle('active',el.dataset.tab===t));
  $('study-muscle').style.display=t==='muscle'?'block':'none';
  $('study-scale').style.display=t==='scale'?'block':'none';
  if(t==='muscle') renderMuscles(); else renderScales();
}
function renderMuscles(){
  const kw=($('muscleSearch').value||'').trim().toLowerCase();
  const list=MUSCLES.filter(m=>!kw||m.name.toLowerCase().includes(kw));
  $('muscleCount').textContent=`共 ${list.length} 块肌肉`;
  $('muscleGrid').innerHTML = list.length ? list.map(m=>`
    <div class="muscle-card">
      ${m.image?`<img class="muscle-img" src="${esc(m.image)}" alt="${esc(m.name)}" loading="lazy" onerror="this.style.display='none'">`:''}
      <div class="muscle-body">
        <div class="muscle-name">${esc(m.name)}</div>
        ${m.origin?`<div class="muscle-field"><b>起点</b>${esc(cleanTail(m.origin))}</div>`:''}
        ${m.insertion?`<div class="muscle-field"><b>止点</b>${esc(cleanTail(m.insertion))}</div>`:''}
        ${m.action?`<div class="muscle-field"><b>功能</b>${esc(cleanTail(m.action))}</div>`:''}
        ${m.nerve?`<div class="muscle-field nerve"><b>神经</b>${esc(m.nerve)}</div>`:''}
      </div>
    </div>`).join('') : `<div class="empty-state"><p>没有找到匹配的肌肉</p></div>`;
}

// ---------- 翻卡测试 ----------
function openMuscleTest(){ $('muscleTestModal').style.display='grid'; $('testSetup').style.display='flex'; $('testStage').style.display='none'; }
function closeMuscleTest(){ $('muscleTestModal').style.display='none'; }
function beginMuscleTest(){
  const n=Math.max(1,Math.min(MUSCLES.length,parseInt($('testCount').value)||10));
  state.testCards=shuffle(MUSCLES).slice(0,n); state.testIdx=0; state.testFlipped=false;
  $('testSetup').style.display='none'; $('testStage').style.display='block';
  renderTestCard();
}
function renderTestCard(){
  const c=state.testCards[state.testIdx];
  if(!c) return;
  $('testIdx').textContent=(state.testIdx+1)+'/'+state.testCards.length;
  $('testBar').style.width=((state.testIdx+1)/state.testCards.length*100)+'%';
  $('testQuestion').textContent=c.name;
  $('flipCard').classList.toggle('flipped',state.testFlipped);
  $('testAnswer').innerHTML=`
    <h3>${esc(c.name)}</h3>
    ${c.image?`<img src="${esc(c.image)}" alt="${esc(c.name)}" onerror="this.style.display='none'">`:''}
    ${c.origin?`<div class="fld"><b>起点：</b>${esc(cleanTail(c.origin))}</div>`:''}
    ${c.insertion?`<div class="fld"><b>止点：</b>${esc(cleanTail(c.insertion))}</div>`:''}
    ${c.action?`<div class="fld"><b>功能：</b>${esc(cleanTail(c.action))}</div>`:''}
    ${c.nerve?`<div class="fld"><b>神经：</b>${esc(c.nerve)}</div>`:''}`;
}
function flipCard(){ state.testFlipped=!state.testFlipped; $('flipCard').classList.toggle('flipped',state.testFlipped); }
function nextTestCard(){ state.testFlipped=false; state.testIdx=(state.testIdx+1)%state.testCards.length; renderTestCard(); }
function prevTestCard(){ state.testFlipped=false; state.testIdx=(state.testIdx-1+state.testCards.length)%state.testCards.length; renderTestCard(); }

// ---------- 学习页：量表 ----------
function renderScaleFilter(){
  const topics=['全部','Berg','Brunnstrom','Ashworth','Barthel','Fugl','平衡','肌力','肌张力','疼痛','日常生活活动','步态','儿童','心肺功能'];
  $('scaleFilter').innerHTML=topics.map(t=>`<span class="scale-tag ${t===state.scaleTopic?'active':''}" onclick="setScaleTopic('${t}')">${t}</span>`).join('');
}
function setScaleTopic(t){ state.scaleTopic=t; renderScaleFilter(); renderScales(); }
function renderScales(){
  renderScaleFilter();
  const kw=($('scaleSearch').value||'').trim().toLowerCase();
  let list=SCALES.filter(s=>{
    const okT=state.scaleTopic==='全部'||s.topics.some(t=>t===state.scaleTopic)||s.title.includes(state.scaleTopic)||s.body.includes(state.scaleTopic);
    const okK=!kw||s.title.toLowerCase().includes(kw)||s.body.toLowerCase().includes(kw);
    return okT&&okK;
  });
  $('scaleCount').textContent=`共 ${list.length} 条`;
  $('scaleGrid').innerHTML=list.length?list.map(s=>`
    <div class="scale-card">
      <h3>${esc(s.title.length>24?s.title.slice(0,24)+'…':s.title)}</h3>
      ${s.topics.length?`<div class="scale-topics">${s.topics.slice(0,5).map(t=>`<span>${esc(t)}</span>`).join('')}</div>`:''}
      <div class="scale-body">${esc(s.body)}</div>
      <div class="scale-src">来源：${esc(s.source)}</div>
    </div>`).join(''):`<div class="empty-state"><p>没有找到匹配的量表</p></div>`;
}

// ---------- 初始化 ----------
function init(){
  state.subject = SUBJECTS.find(s=>subjCount(s)>0) || SUBJECTS[0];
  selectMode('direct');
  renderHome();
}
init();
