const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const api=async(p,o)=>{const r=await fetch(p,o);if(!r.ok)throw new Error((await r.text()).slice(0,200));return r.json();};
const eM=v=>v==null?'—':'€'+Number(v).toFixed(Number(v)%1?1:0)+'M';
const initials=n=>n.split(' ').map(w=>w[0]).slice(0,2).join('').toUpperCase();
// streaming reveal — types out an element's text so ai_query outputs read as generated live
function typewrite(el,ms){if(!el)return;const txt=el.textContent||'';if(!txt||txt.length>700){return;}
  el.textContent='';el.classList.add('typing');let i=0;
  const step=()=>{i+=Math.max(1,Math.round(txt.length/120));el.textContent=txt.slice(0,i);
    if(i<txt.length)setTimeout(step,ms||16);else el.classList.remove('typing');};
  step();}
const gprCls=g=>g>=80?'':'lo';
function h32(s){let h=0;for(let i=0;i<s.length;i++)h=(h*31+s.charCodeAt(i))>>>0;return h;}
const rnd=(seed,lo,hi)=>lo+(h32(seed)%1000)/1000*(hi-lo);
let SQUAD=[];
/* scenario (Lakebase what-if) state */
let SCEN=[], COMPARE=null, ACTIVE='current';
/* injury & load-risk (L3) */
let INJURY=[], INJ_BY={};
const bandCls=b=>({High:'red',Elevated:'amber',Moderate:'blue',Low:'green'}[b]||'');
const availCls=a=>({Doubtful:'red',Monitor:'amber',Available:'green'}[a]||'');
const dM=v=>{v=Number(v)||0;return (v>0?'+':v<0?'−':'')+'€'+Math.abs(v).toFixed(1)+'M';};
const eMv=v=>'€'+Number(v||0).toFixed(Math.abs(Number(v||0))>=100?0:1)+'M';
const scenById=id=>COMPARE&&COMPARE.scenarios.find(s=>s.scenario_id===id);
const activeScen=()=>ACTIVE==='current'?null:scenById(ACTIVE);

/* ---------------- nav + subtabs + router ---------------- */
function showView(v){
  $$('#nav .navitem').forEach(x=>x.classList.toggle('active',x.dataset.view===v));
  $$('.view').forEach(x=>x.classList.toggle('active',x.id==='view-'+v));
  window.scrollTo(0,0);
}
$$('#nav .navitem').forEach(it=>it.onclick=()=>{location.hash=it.dataset.view;});
function wireTabs(tabsSel){
  $$(tabsSel+' .tab').forEach(t=>t.onclick=()=>{
    const root=t.closest('.view');
    $$(tabsSel+' .tab').forEach(x=>x.classList.remove('active'));t.classList.add('active');
    $$('.subview',root).forEach(s=>s.classList.toggle('active',s.id==='sub-'+t.dataset.sub));
  });
}
function selectSub(view,sub){
  const tabs=view==='scouting'?'#scoutTabs':'#squadTabs';
  const t=$$(tabs+' .tab').find(x=>x.dataset.sub===sub); if(t)t.click();
}
const AGENT_SUBS=['physio','nutrition','coach','financial','transfer'];
function selectAgentSub(sub,param){
  const loaders={transfer:loadTransfer,physio:loadPhysio,nutrition:loadNutrition,coach:loadOpposition,financial:loadFfp};
  if(!loaders[sub])sub='physio';
  $$('#agentTabs .tab').forEach(t=>t.classList.toggle('active',t.dataset.sub===sub));
  $$('#view-agents .subview').forEach(s=>s.classList.toggle('active',s.id==='sub-'+sub));
  window.scrollTo(0,0);
  try{loaders[sub](param);}catch(e){console.error('agent load',sub,e);}
}
function route(){
  const raw=location.hash.replace(/^#/,'')||'home';
  const [path,query]=raw.split('?');
  const parts=path.split('/');
  const view=parts[0];
  if(view==='player'){ showView('squad'); openPlayer(parts[1]); setExplainer(null); return; }
  showView(view);
  if(view==='agents'){ const sub=AGENT_SUBS.includes(parts[1])?parts[1]:'physio'; selectAgentSub(sub, parts[2]); setExplainer(sub); return; }
  if(view==='squad'||view==='scouting'){ if(parts[1]) selectSub(view,parts[1]); setExplainer(null); return; }
  if(view==='clips'){ setExplainer('clips'); const q=new URLSearchParams(query||'').get('q'); if(q){$('#clipInput').value=q;runClip(q);} return; }
  if(view==='ask'){ setExplainer('ask'); askStartRot(); return; }
  askStopRot();
  setExplainer(null);
}
window.addEventListener('hashchange',route);

/* ---------------- HOME ---------------- */
const HOME_CHIPS=["Top 5 LWs under €20M, good at carrying","Recently scouted players that fit our game model"];
// activity feed — "X added Y to Z" style, matching the product's Updates panel
const FEED=[
 ['eye','Priya Nair','added <b>Max Dowman</b> to Academy Watch',null,'2h'],
 ['act','Marco Bianchi','added <b>Vitor Roque</b> to column Priority on Recruitment Pipeline','13 items','4h'],
 ['eye','James Okafor','added <b>Michael Olise</b> to Wide Forwards',null,'5h'],
 ['act','Alejandro Ferreira','added <b>Cristian Mosquera</b> to column Defenders on Pipeline','11 items','Today'],
 ['eye','Tomasz Kowalski','added <b>Sandro Tonali</b> to Midfield Targets',null,'Today'],
 ['act','Priya Nair','added <b>Morgan Rogers</b> to column Discovery on Recruitment Pipeline','3 items','Jul 2'],
];
const FEED_IC={eye:'<svg viewBox="0 0 24 24"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/></svg>',
  act:'<svg viewBox="0 0 24 24"><path d="M3 12h4l2 6 4-14 2 8h6"/></svg>'};
// 3-band GPR donut (80+ / 70-79 / <70) for the Pinned rail
function railDonut(b80,b70,blt,center,label){
  const parts=[['#16A34A',b80],['#86E0A6',b70],['#F5A623',blt]];
  const total=(b80+b70+blt)||1,r=48,C=2*Math.PI*r;let off=0;
  const seg=parts.map(([c,n])=>{const len=(n/total)*C;const s=`<circle cx="60" cy="60" r="${r}" fill="none" stroke="${c}" stroke-width="16" stroke-dasharray="${len} ${C-len}" stroke-dashoffset="${-off}" transform="rotate(-90 60 60)"/>`;off+=len;return s;}).join('');
  return `<svg width="120" height="120" viewBox="0 0 120 120">${seg}<text x="60" y="57" text-anchor="middle" fill="#0F172A" font-size="26" font-weight="800">${center}</text><text x="60" y="71" text-anchor="middle" fill="#647084" font-size="8" letter-spacing=".3" font-weight="700">${label}</text></svg>`;
}
const statTile=(n,l,cls)=>`<div class="stile"><div class="st-n ${cls||''}">${n}</div><div class="st-l">${l}</div></div>`;
async function loadHome(){
  $('#homeChips').innerHTML=HOME_CHIPS.map(c=>`<span class="chip">${c}</span>`).join('');
  $$('#homeChips .chip').forEach(c=>c.onclick=()=>{location.hash='ask';});
  const homeAsk=$('#homeAsk'); if(homeAsk)homeAsk.addEventListener('keydown',e=>{if(e.key==='Enter')location.hash='ask';});
  const rd=$('#railDate'); if(rd)rd.textContent=new Date().toLocaleDateString('en-GB',{day:'numeric',month:'long',year:'numeric'});
  $('#feed').innerHTML=FEED.map(([ic,who,rest,items,tm])=>`<div class="feedcard">
    <span class="fc-ic">${FEED_IC[ic]||FEED_IC.eye}</span>
    <div class="fc-t">${who} ${rest}</div>
    ${items?`<span class="fc-items">${items} <svg viewBox="0 0 24 24"><path d="M6 9l6 6 6-6"/></svg></span>`:''}
    <span class="fc-time">${tm}</span></div>`).join('');
  const s=await api('/api/summary');
  const ft=SQUAD.filter(p=>p.tier==='First Team');
  const inFt=ft.length?ft:SQUAD;
  const b80=inFt.filter(p=>p.gpr>=80).length,b70=inFt.filter(p=>p.gpr>=70&&p.gpr<80).length,blt=inFt.filter(p=>p.gpr<70).length;
  const you=Math.round(s.totals.avg_gpr||67), LEAGUE_AVG=53, LO=30, HI=Math.max(70,you);
  const pct=v=>Math.max(0,Math.min(100,(v-LO)/(HI-LO)*100));
  const monitor=(typeof INJURY!=='undefined'?INJURY:[]).filter(r=>r.risk_band==='Elevated'||/monitor/i.test(r.availability||'')).length;
  const onLoan=SQUAD.filter(p=>/loan/i.test(p.status||'')).length;
  const exp18=SQUAD.filter(p=>+p.months_left<=18).length, exp24=SQUAD.filter(p=>+p.months_left>18&&+p.months_left<=24).length;
  $('#pinnedSquad').innerHTML=`
    <div class="pin-h"><span class="pin-l"><svg viewBox="0 0 24 24"><circle cx="9" cy="8" r="3"/><path d="M2.6 20a6.4 6.4 0 0 1 12.8 0"/><path d="M16 5.6a3 3 0 0 1 0 5.6M17.8 20a6 6 0 0 0-3-5.2"/></svg> SQUAD</span><span class="pin-x" onclick="location.hash='squad'">EXPLORE →</span></div>
    <div class="squad-donut"><div>${railDonut(b80,b70,blt,inFt.length,'FIRST TEAM')}</div>
      <div class="gband"><div class="gb"><span class="sw" style="background:#16A34A"></span>GPR 80+<b>${b80}</b></div>
        <div class="gb"><span class="sw" style="background:#86E0A6"></span>GPR 70–79<b>${b70}</b></div>
        <div class="gb"><span class="sw" style="background:#F5A623"></span>GPR &lt;70<b>${blt}</b></div></div></div>
    <div class="spec-h">LEAGUE GPR SPECTRUM</div>
    <div class="spectrum2"><div class="track"></div><span class="mk avg" style="left:${pct(LEAGUE_AVG)}%"></span><span class="mk you" style="left:${pct(you)}%" data-you="You · ${you}"></span></div>
    <div class="spec-lab"><span>Lowest (${LO})</span><span>League avg ${LEAGUE_AVG}</span><span>Highest (${HI})</span></div>
    <div class="statgrid">${statTile(monitor,'On watch',monitor>0?'amber':'')}${statTile(onLoan,'On Loan')}${statTile(exp18,'Expiring ≤18mo',exp18>0?'red':'')}${statTile(exp24,'Expiring 18–24mo',exp24>0?'amber':'')}</div>`;
  const targets=SQUAD.filter(p=>p.tier==='Target');
  const reported=new Set(SCOUT_REPORTS.map(r=>r.name));
  const without=targets.filter(p=>!reported.has(p.name)).length;
  const posCount={};targets.forEach(p=>{const k=(p.positions||'').split(',')[0].trim()||'—';posCount[k]=(posCount[k]||0)+1;});
  const topPos=Object.entries(posCount).sort((a,b)=>b[1]-a[1]).slice(0,4);
  $('#pinnedScouting').innerHTML=`
    <div class="pin-h"><span class="pin-l"><svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></svg> SCOUTING</span><span class="pin-x" onclick="location.hash='scouting'">EXPLORE →</span></div>
    <div class="scout-big"><div class="sb-n">${targets.length}</div><div class="sb-l">Players on a watchlist</div></div>
    <div class="statgrid two"><div class="stile"><div class="st-n red">${without}</div><div class="st-l">without report</div></div>
      <div class="stile"><div class="st-n red">${Math.max(0,targets.length-2)}</div><div class="st-l">no action <span class="muted">(30 days)</span></div></div></div>
    <div class="pos-grid">${topPos.map(([k,n])=>`<div class="ptile"><div class="pt-l">${POS_LABEL[k]||k}</div><div class="pt-n">${n}</div></div>`).join('')}</div>`;
}
const POS_LABEL={RW:'Right Wing',LW:'Left Wing',ST:'Number 9',CF:'Number 9',CM:'Number 8',DM:'Number 6',CAM:'Creator',CB:'Centre-back',RB:'Right-back',LB:'Left-back',GK:'Goalkeeper'};

/* ---------------- SCOUTING ---------------- */
let SCOUT=[];
async function loadScouting(){
  SCOUT=await api('/api/scouting');
  const lists=['All Targets',...[...new Set(SCOUT.map(s=>s.list_name))]];
  $('#watchFilters').innerHTML=lists.map((l,i)=>`<span class="chip ${i===0?'on':''}">${l}</span>`).join('');
  $$('#watchFilters .chip').forEach(c=>c.onclick=()=>{$$('#watchFilters .chip').forEach(x=>x.classList.remove('on'));c.classList.add('on');renderWatch(c.textContent);});
  renderWatch('All Targets');
  // reports
  const reps=[]; // from scout_reports via players — fetch per not available; use SQUAD + known
  $('#reportsBody').innerHTML=SCOUT_REPORTS.map(r=>`<tr><td><div class="pname"><span class="pmini">${initials(r.name)}</span>${r.name}</div></td><td>${r.scout}</td><td class="muted">${r.date}</td><td><span class="pill ${r.status==='Priority'?'amber':r.status==='Active'?'green':''}">${r.status}</span></td><td class="muted" style="white-space:normal;max-width:420px">${r.summary}</td></tr>`).join('');
  // Boards / Shadow Team — intentionally left empty (SOON tabs).
  $('#sub-boards').innerHTML='';
  $('#sub-shadow').innerHTML='';
}
function renderWatch(list){
  const rows=SCOUT.filter(s=>list==='All Targets'||s.list_name===list);
  const byPlayer={};rows.forEach(r=>{(byPlayer[r.player_id]=byPlayer[r.player_id]||{...r,lists:[]});});
  SCOUT.forEach(r=>{if(byPlayer[r.player_id])byPlayer[r.player_id].lists.push(r.list_name.replace(/^.*—\s*/,''));});
  const uniq=Object.values(byPlayer).filter(r=>list==='All Targets'||r.lists.some(l=>list.includes(l))||r.list_name===list);
  const show=(list==='All Targets')?Object.values(byPlayer):rows;
  $('#watchBody').innerHTML=show.map(r=>`<tr class="clickable" onclick="location.hash='player/${r.player_id}'">
    <td><div class="pname"><span class="pmini">${initials(r.name)}</span>${r.name}</div></td>
    <td class="muted">${r.club}</td><td class="muted">${r.positions}</td><td class="muted">${r.country}</td>
    <td class="right"><span class="gpr ${gprCls(r.gpr)}">${r.gpr}</span></td>
    <td><span class="pill blue">${(byPlayer[r.player_id].lists[0]||r.list_name.replace(/^.*—\s*/,''))}</span></td>
    <td class="right">${r.months_left}</td></tr>`).join('');
}
const SCOUT_REPORTS=[
 {name:'Max Dowman',scout:'Priya Nair',date:'2025-08-11',status:'Active',summary:'Generational academy talent, fearless dribbler; manage minutes. Long-term first-team projection.'},
 {name:'Vitor Roque',scout:'Marco Bianchi',date:'2025-07-28',status:'Priority',summary:'Explosive penalty-box striker, relentless pressing; needs link-up refinement. Strong value at current clause.'},
 {name:'Michael Olise',scout:'James Okafor',date:'2025-08-05',status:'Priority',summary:'Elite creator from the right, set-piece value; injury history a flag. Top-tier fit, premium fee.'},
 {name:'Cristian Mosquera',scout:'Alejandro Ferreira',date:'2025-08-10',status:'Priority',summary:'Composed ball-playing CB, elite recovery pace, high system fit; priority buy-and-develop.'},
 {name:'Morgan Rogers',scout:'Priya Nair',date:'2025-08-08',status:'Active',summary:'Powerful ball-carrier through the half-spaces; final-third efficiency improving. Good value, rising fee.'},
 {name:'Sandro Tonali',scout:'Tomasz Kowalski',date:'2025-08-09',status:'Active',summary:'Deep-lying orchestrator, excellent range of passing; needs consistent minutes. Fits our build-out.'},
];

/* ---------------- SQUAD ---------------- */
const PITCH=[
 [{pos:'GK',id:'p_raya'}],
 [{pos:'RB',id:'p_white'},{pos:'CB',id:'p_saliba'},{pos:'CB',id:'p_gabriel'},{pos:'LB',id:'p_timber'}],
 [{pos:'DM',id:'p_rice'},{pos:'CM',id:'p_odegaard'},{pos:'CM',id:'p_norgaard'}],
 [{pos:'RW',id:'p_saka'},{pos:'ST',id:null,open:'Target: Álvarez'},{pos:'LW',id:null,open:'Target: Barcola'}],
];
function loadSquad2(){
  renderSquadKpis();
  renderPitchAndFT();      // base render; re-run with scenario overlay on selection
  renderAvailability();
  const acad=SQUAD.filter(p=>p.tier==='Academy');
  $('#acadBody').innerHTML=acad.map(p=>{const r=Math.round(rnd(p.player_id,45,80));return `<tr class="clickable" onclick="location.hash='player/${p.player_id}'">
    <td><div class="pname"><span class="pmini">${initials(p.name)}</span>${p.name}</div></td>
    <td class="muted">${p.positions}</td><td class="right muted">${p.age}</td><td class="right"><span class="gpr ${gprCls(p.gpr)}">${p.gpr}</span></td>
    <td><span class="readbar"><span class="b"><i style="width:${r}%"></i></span><span class="muted" style="font-size:11px">${r}%</span></span></td>
    <td><span class="pill amber">Prospect</span></td></tr>`;}).join('');
  // contracts
  const cont=SQUAD.filter(p=>p.contract_end).sort((a,b)=>(a.contract_end>b.contract_end?1:-1));
  $('#contractsBody').innerHTML=cont.map(p=>`<tr class="clickable" onclick="location.hash='player/${p.player_id}'">
    <td><div class="pname"><span class="pmini">${initials(p.name)}</span>${p.name}</div></td>
    <td class="right muted">${p.age}</td><td><span class="pill">${p.tier}</span></td>
    <td>${p.contract_end}</td><td class="right">${p.release_clause?eM(p.release_clause)+' clause':'—'}</td>
    <td><span class="pill ${p.transfer_status==='Not For Sale'?'red':p.transfer_status==='Available'?'green':'blue'}">${p.transfer_status||'—'}</span></td>
    <td class="muted">2025-08-18</td></tr>`).join('');
  // Financials / Analysis — intentionally left empty (SOON tabs).
  $('#sub-financials').innerHTML='';
  $('#sub-analysis').innerHTML='';
}
function placeholder(t,d){return `<div class="placeholder"><div class="pi"><svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M8 4v16"/></svg></div><h3>${t} <span class="soonbadge">SOON</span></h3><p>${d}</p></div>`;}

/* ---------------- SCENARIOS (Lakebase what-if) ---------------- */
const lastName=n=>String(n||'').split(' ').slice(-1)[0];
const shortScen=n=>{n=String(n||'').trim();
  const lead=n.match(/^Scenario\s+[A-Za-z0-9]+/);if(lead)return lead[0];
  const head=n.split(/\s[-–—]\s/)[0].trim();
  if(head.length<=24)return head;
  return head.slice(0,22).replace(/\s\S*$/,'')+'…';};
function moveSets(scen){
  const sold=new Set(),promoted=new Set(),bought=[];
  if(scen)for(const l of (scen.move_lines||[])){
    if(l.action==='sell')sold.add(l.player_id);
    else if(l.action==='promote')promoted.add(l.player_id);
    else if(l.action==='buy')bought.push(l);
  }
  return {sold,promoted,bought};
}
function renderSquadKpis(){
  const scen=activeScen();
  const agg=scen?scen:COMPARE&&COMPARE.current;
  const value=agg?agg.squad_value:SQUAD.reduce((s,p)=>s+ +p.gpv,0);
  const wage=agg?agg.wage_bill:SQUAD.reduce((s,p)=>s+(p.tier==='First Team'?+p.wage_per_yr:0),0);
  const gains=scen?scen.capital_gains:48;
  const players=agg?agg.n_players:SQUAD.length;
  const gc=gains>=0?'var(--green)':'var(--red)';
  $('#squadKpis').innerHTML=`
    <div class="kpi"><div class="v">${eMv(value)}</div><div class="l">SQUAD VALUE${scen?' (SCENARIO)':''}</div></div>
    <div class="kpi"><div class="v blue">${eMv(wage)}</div><div class="l">YEARLY WAGE BILL</div></div>
    <div class="kpi"><div class="v" style="color:${gc}">${(gains>=0?'+':'')+eMv(gains)}</div><div class="l">CAPITAL GAINS${scen?'':' (YTD)'}</div></div>
    <div class="kpi"><div class="v">${players}</div><div class="l">TOTAL PLAYERS</div></div>`;
}
function renderPitchAndFT(){
  const scen=activeScen();const {sold,promoted,bought}=moveSets(scen);
  const byId=Object.fromEntries(SQUAD.map(p=>[p.player_id,p]));
  // pitch: place bought players into open slots (in order)
  let bIdx=0;
  $('#pitch').innerHTML=PITCH.map(lane=>`<div class="lane">${lane.map(s=>{
    const p=byId[s.id];
    if(p){const isSold=sold.has(p.player_id);
      return `<div class="slot ${isSold?'sold':''}" onclick="location.hash='player/${p.player_id}'"><div class="pos">${s.pos}</div><div class="nm">${lastName(p.name)}</div><div class="g">${isSold?'SOLD':'GPR '+p.gpr}</div></div>`;}
    const b=bought[bIdx++];
    if(b)return `<div class="slot incoming"><div class="pos">${s.pos}</div><div class="nm">${lastName(b.name)}</div><div class="g" style="color:var(--amber-tx)">IN · ${eMv(b.value_delta)}</div></div>`;
    return `<div class="slot open"><div class="pos">${s.pos}</div><div class="nm">${s.open||'Open'}</div></div>`;
  }).join('')}</div>`).join('');
  // first-team table with scenario markers
  const ft=SQUAD.filter(p=>p.tier==='First Team').sort((a,b)=>b.gpr-a.gpr);
  const extra=[...promoted].map(id=>byId[id]).filter(Boolean).filter(p=>p.tier!=='First Team');
  const rows=[...ft,...extra];
  $('#ftBody').innerHTML=rows.map(p=>{
    const isSold=sold.has(p.player_id),isProm=promoted.has(p.player_id);
    const mk=isSold?'<span class="mkpill sold">SOLD</span>':isProm?'<span class="mkpill promoted">PROMOTED</span>':'';
    const inj=INJ_BY[p.player_id];const rdot=inj?`<span class="rdot ${bandCls(inj.risk_band)}" title="Load risk: ${inj.risk_band} (${(+inj.risk_score).toFixed(0)}) · ${inj.availability}"></span>`:'';
    return `<tr class="clickable ${isSold?'sold':''}" onclick="location.hash='player/${p.player_id}'">
    <td><span class="pill">${p.positions.split(',')[0]}</span></td>
    <td><div class="pname"><span class="pmini">${initials(p.name)}</span>${p.name}${rdot}${mk}</div></td>
    <td class="right muted">${p.age}</td><td class="right"><span class="gpr ${gprCls(p.gpr)}">${p.gpr}</span></td>
    <td class="right muted">${p.minutes}</td><td class="right">${eM(p.wage_per_yr)}</td><td class="right">${eM(p.gpv)}</td>
    <td class="right">${eM(p.est_valuation_low)}–${(+p.est_valuation_high).toFixed(0)}</td>
    <td class="right">${p.months_left}${p.months_left<24?' <span class="pill red">low</span>':''}</td></tr>`;}).join('');
}
function tile(k,v,delta,goodUp){
  let d='';
  if(delta!==undefined&&delta!==null){const dir=Math.abs(delta)<0.05?'flat':((delta>0)===goodUp?'up':'down');
    d=`<div class="d ${dir}">${dM(delta)} vs Current</div>`;}
  return `<div class="itile"><div class="k">${k}</div><div class="v">${v}</div>${d}</div>`;
}
function renderImpact(){
  const box=$('#scenarioImpact');const scen=activeScen();
  if(!scen){box.innerHTML='';return;}
  const model=(COMPARE&&COMPARE.valuation_model)||'gpv-fallback';
  const modelReal=model&&model!=='gpv-fallback'&&!/fallback|down|error/i.test(model);
  const d=scen.deltas||{};
  const gainc=scen.capital_gains>=0?'var(--green)':'var(--red)';
  box.innerHTML=`<div class="impactcard">
    <div class="ih"><div><h3>${scen.name}</h3><div class="sub">${scen.notes||'What-if scenario'} · formation ${scen.base_formation||'—'}</div></div>
      <span class="badge ${modelReal?'':'warn'}" title="${model}">${modelReal?'Valuation model':'GPV baseline'}</span></div>
    <div class="itiles">
      ${tile('Squad value',eMv(scen.squad_value),d.squad_value,true)}
      ${tile('Wage bill',eMv(scen.wage_bill),d.wage_bill,false)}
      ${tile('Capital gains','<span style="color:'+gainc+'">'+(scen.capital_gains>=0?'+':'')+eMv(scen.capital_gains)+'</span>')}
      ${tile('Net spend',eMv(scen.net_spend))}
    </div>
    <div class="movelist"><div class="tablewrap"><table><thead><tr><th>Player</th><th>Action</th><th class="right">Δ Value</th><th class="right">Δ Wage</th><th class="right">Capital gain</th><th>Note</th></tr></thead><tbody>
      ${(scen.move_lines||[]).map(l=>`<tr><td><div class="pname"><span class="pmini">${initials(l.name)}</span>${l.name}</div></td>
        <td><span class="act ${l.action}">${l.action}</span></td>
        <td class="right deltacell ${l.value_delta>0?'up':l.value_delta<0?'down':''}">${l.value_delta?dM(l.value_delta):'—'}</td>
        <td class="right deltacell ${l.wage_delta<0?'up':l.wage_delta>0?'down':''}">${l.wage_delta?dM(l.wage_delta):'—'}</td>
        <td class="right deltacell ${l.capital_gain>0?'up':l.capital_gain<0?'down':''}">${l.capital_gain?dM(l.capital_gain):'—'}</td>
        <td class="muted" style="white-space:normal;max-width:220px">${l.note||''}</td></tr>`).join('')}
    </tbody></table></div></div></div>`;
}
function renderCompare(){
  const box=$('#scenarioCompare');
  if(!COMPARE||!COMPARE.scenarios.length){box.innerHTML='';return;}
  const cur=COMPARE.current,scs=COMPARE.scenarios;
  const cols=[{name:'Current',a:cur},...scs.map(s=>({name:shortScen(s.name),a:s}))];
  const bestVal=Math.max(...cols.map(c=>c.a.squad_value));
  const bestGain=Math.max(...scs.map(s=>s.capital_gains),0);
  const metric=(label,get,fmt,bestTest)=>`<tr><td class="metric">${label}</td>${cols.map(c=>{
    const v=get(c.a);return `<td class="scol ${bestTest&&bestTest(c.a)?'best':''}">${fmt(v)}</td>`;}).join('')}</tr>`;
  box.innerHTML=`<div class="section-h">Compare — Current vs scenarios</div>
    <div class="comparewrap tablewrap"><table><thead><tr><th>Metric</th>${cols.map(c=>`<th class="scol">${c.name}</th>`).join('')}</tr></thead><tbody>
    ${metric('Squad value',a=>a.squad_value,eMv,a=>a.squad_value===bestVal)}
    ${metric('Wage bill',a=>a.wage_bill,eMv)}
    ${metric('Capital gains',a=>a.capital_gains||0,v=>(v>0?'+':'')+eMv(v),a=>bestGain>0&&a.capital_gains===bestGain)}
    ${metric('Net spend',a=>a.net_spend||0,eMv)}
    ${metric('Players',a=>a.n_players,v=>v)}
    </tbody></table></div>
    <div class="tblnote">Squad value from the ${COMPARE.valuation_model&&COMPARE.valuation_model!=='gpv-fallback'?'what-if valuation model':'GPV baseline'} · scenarios persisted transactionally in Lakebase (Postgres).</div>`;
}
function renderPlanning(){renderSquadKpis();renderPitchAndFT();renderImpact();renderCompare();renderScenarioRow();}
function renderAvailability(){
  const box=$('#availCard');if(!box)return;
  if(!INJURY.length){box.innerHTML='';return;}
  const n=b=>INJURY.filter(r=>r.risk_band===b).length;
  const avail=a=>INJURY.filter(r=>r.availability===a).length;
  const flagged=INJURY.filter(r=>r.risk_band==='Elevated'||r.risk_band==='High').slice(0,6);
  const maxScore=Math.max(...INJURY.map(r=>+r.risk_score));
  box.innerHTML=`<div class="section-h">Availability &amp; load risk <span class="soonbadge" style="background:var(--green-bg);color:var(--green-tx)">LIVE MODEL</span></div>
  <div class="impactcard">
    <div class="ih"><div><h3>Injury &amp; load-risk</h3><div class="sub">Model over synthetic physical/tracking data · scored into Delta · answerable in Acme Scout</div></div>
      <div style="display:flex;gap:8px">
        <span class="availtag green">${avail('Available')} Available</span>
        <span class="availtag amber">${avail('Monitor')} Monitor</span>
        <span class="availtag red">${avail('Doubtful')} Doubtful</span></div></div>
    <div class="risklist">
      ${flagged.map(r=>{const w=Math.round(+r.risk_score/maxScore*100);
        return `<div class="riskrow clickable" onclick="location.hash='player/${r.player_id}'">
          <div class="pname"><span class="pmini">${initials(r.name)}</span>${r.name}</div>
          <div class="rbarwrap"><div class="rbar"><i class="${bandCls(r.risk_band)}" style="width:${w}%"></i></div></div>
          <span class="pill ${bandCls(r.risk_band)}">${r.risk_band} · ${(+r.risk_score).toFixed(0)}</span>
          <span class="availpill ${availCls(r.availability)}">${r.availability}</span>
          <span class="muted rnote">${r.risk_note||''}</span></div>`;}).join('')}
    </div></div>`;
}
function renderScenarioRow(){
  const row=$('#scenarioRow');if(!row)return;
  const pills=[{id:'current',name:'Current',seeded:true},...SCEN.map(s=>({id:s.scenario_id,name:s.name,seeded:!!s.seeded}))];
  row.innerHTML=pills.map(p=>{
    const deletable=p.id!=='current'&&!p.seeded;
    const label=p.id==='current'?'Current':shortScen(p.name)+'<span class="lb">LAKEBASE</span>';
    const del=deletable?`<span class="scdel" data-del="${p.id}" title="Delete scenario" aria-label="Delete scenario">×</span>`:'';
    return `<div class="sc ${p.id===ACTIVE?'active':''}" data-id="${p.id}">${label}${del}</div>`;
  }).join('')
    +`<div class="sc add" id="createScen">+ Create Scenario</div>`;
  $$('#scenarioRow .sc[data-id]').forEach(el=>el.onclick=e=>{
    if(e.target.classList.contains('scdel'))return;   // × handled separately
    ACTIVE=el.dataset.id;renderPlanning();});
  $$('#scenarioRow .scdel').forEach(el=>el.onclick=e=>{e.stopPropagation();confirmDeleteScenario(el.dataset.del);});
  $('#createScen').onclick=()=>openScenBuilder();
}
/* ---- delete scenario (user-created only; seeded are protected server-side too) ---- */
function cfClose(){$('#confirmModal')&&$('#confirmModal').classList.remove('open');}
$('#confirmModal')&&($('#confirmModal').onclick=e=>{if(e.target.id==='confirmModal')cfClose();});
function confirmDeleteScenario(id){
  const s=SCEN.find(x=>x.scenario_id===id)||{};
  const nm=(s.name||id).replace(/</g,'&lt;');
  $('#confirmCard').innerHTML=`
    <div class="cfh"><h3>Delete scenario</h3></div>
    <div class="cfbody">Permanently delete <b>${nm}</b> and its moves from Lakebase? This cannot be undone.</div>
    <div class="cffoot"><span class="sp" id="cfMsg"></span>
      <button class="btn grey" id="cfCancel">Cancel</button>
      <button class="btn danger" id="cfDelete">Delete scenario</button></div>`;
  $('#confirmModal').classList.add('open');
  $('#cfCancel').onclick=cfClose;
  $('#cfDelete').onclick=()=>doDeleteScenario(id);
}
async function doDeleteScenario(id){
  const msg=$('#cfMsg');msg.textContent='Deleting from Lakebase…';$('#cfDelete').disabled=true;
  try{
    await api('/api/scenario/'+encodeURIComponent(id),{method:'DELETE'});
    cfClose();
    if(ACTIVE===id)ACTIVE='current';
    await initScenarios();   // reload from Lakebase — UI updates immediately
  }catch(e){msg.textContent=e.message;$('#cfDelete').disabled=false;}
}
async function initScenarios(){
  try{
    SCEN=await api('/api/scenarios');
    COMPARE=await api('/api/scenarios/compare');
  }catch(e){console.error('scenarios load failed',e);SCEN=[];COMPARE={current:{squad_value:SQUAD.reduce((s,p)=>s+ +p.gpv,0),wage_bill:0,capital_gains:0,net_spend:0,n_players:SQUAD.length},scenarios:[],valuation_model:'gpv-fallback'};}
  if(ACTIVE!=='current'&&!scenById(ACTIVE))ACTIVE='current';
  renderPlanning();
}
/* ---- scenario builder modal ---- */
let SCEN_MOVES=[];
const ACTIONS=['keep','sell','promote','buy'];
function scenClose(){$('#scenModal').classList.remove('open');}
$('#scenModal')&&($('#scenModal').onclick=e=>{if(e.target.id==='scenModal')scenClose();});
function moveRowHtml(m,i){
  const opts=SQUAD.map(p=>`<option value="${p.player_id}" ${p.player_id===m.player_id?'selected':''}>${p.name} · ${p.tier}</option>`).join('');
  const acts=ACTIONS.map(a=>`<option ${a===m.action?'selected':''}>${a}</option>`).join('');
  return `<div class="moverow" data-i="${i}">
    <div class="field"><label>Player</label><select class="mv-player">${opts}</select></div>
    <div class="field"><label>Action</label><select class="mv-action">${acts}</select></div>
    <div class="field"><label>Adj. wage €M</label><input class="mv-wage" type="number" step="0.1" value="${m.adjusted_wage??''}"/></div>
    <div class="field"><label>Adj. value €M</label><input class="mv-value" type="number" step="1" value="${m.adjusted_value??''}"/></div>
    <button class="rm" title="Remove">×</button></div>`;
}
function prefillMove(i){const p=SQUAD.find(x=>x.player_id===SCEN_MOVES[i].player_id);if(!p)return;
  const act=SCEN_MOVES[i].action;
  SCEN_MOVES[i].adjusted_wage=act==='sell'?0:act==='promote'?Math.max(1,Math.round(+p.wage_per_yr*3)/1):+p.wage_per_yr;
  SCEN_MOVES[i].adjusted_value=act==='sell'?+p.est_valuation_high:+p.gpv;}
function renderMoves(){
  $('#scenMoves').innerHTML=SCEN_MOVES.map(moveRowHtml).join('')||'<div class="muted" style="font-size:12.5px;padding:4px 2px">No moves yet — add one to model a transfer.</div>';
  $$('#scenMoves .moverow').forEach(row=>{const i=+row.dataset.i;
    row.querySelector('.mv-player').onchange=e=>{SCEN_MOVES[i].player_id=e.target.value;prefillMove(i);renderMoves();};
    row.querySelector('.mv-action').onchange=e=>{SCEN_MOVES[i].action=e.target.value;prefillMove(i);renderMoves();};
    row.querySelector('.mv-wage').onchange=e=>SCEN_MOVES[i].adjusted_wage=parseFloat(e.target.value);
    row.querySelector('.mv-value').onchange=e=>SCEN_MOVES[i].adjusted_value=parseFloat(e.target.value);
    row.querySelector('.rm').onclick=()=>{SCEN_MOVES.splice(i,1);renderMoves();};});
}
async function openScenBuilder(existingId){
  let name='',formation='4-3-3',notes='';SCEN_MOVES=[];let editId='';
  if(existingId){try{const s=await api('/api/scenario/'+existingId);name=s.name;formation=s.base_formation||'4-3-3';notes=s.notes||'';editId=s.scenario_id;
    SCEN_MOVES=(s.moves||[]).map(m=>({player_id:m.player_id,action:m.action,adjusted_wage:m.adjusted_wage,adjusted_value:m.adjusted_value,note:m.note}));}catch(e){}}
  const forms=['4-3-3','4-2-3-1','3-4-3','4-4-2'];
  $('#scenBuilder').innerHTML=`
    <div class="sbh"><span class="close" onclick="scenClose()">×</span>
      <h2>${editId?'Edit scenario':'Create scenario'}</h2>
      <div class="meta">Model a squad plan — sells, promotions and buys. Saved transactionally to <b>Lakebase</b>.</div></div>
    <div class="sbbody">
      <div class="sbrow">
        <div class="field"><label>Scenario name</label><input id="scenName" placeholder="e.g. Scenario B — Sell Saliba, promote Dowman" value="${name.replace(/"/g,'&quot;')}"/></div>
        <div class="field"><label>Base formation</label><select id="scenForm">${forms.map(f=>`<option ${f===formation?'selected':''}>${f}</option>`).join('')}</select></div>
      </div>
      <div class="field"><label>Notes</label><input id="scenNotes" placeholder="What-if rationale…" value="${notes.replace(/"/g,'&quot;')}"/></div>
      <div class="movehdr"><div class="section-h">Moves</div><button class="addmove" id="addMove">+ Add move</button></div>
      <div id="scenMoves"></div>
    </div>
    <div class="sbfoot"><span class="sp" id="scenSaveMsg"></span>
      <button class="btn grey" onclick="scenClose()">Cancel</button>
      <button class="btn" id="scenSaveBtn">${editId?'Save changes':'Save scenario'}</button></div>`;
  $('#scenBuilder').dataset.edit=editId;
  renderMoves();
  $('#addMove').onclick=()=>{const p=SQUAD[0];SCEN_MOVES.push({player_id:p.player_id,action:'sell'});prefillMove(SCEN_MOVES.length-1);renderMoves();};
  $('#scenSaveBtn').onclick=saveScenario;
  $('#scenModal').classList.add('open');
}
async function saveScenario(){
  const name=$('#scenName').value.trim();const msg=$('#scenSaveMsg');
  if(!name){msg.textContent='Name required.';return;}
  const payload={scenario_id:$('#scenBuilder').dataset.edit||undefined,name,
    base_formation:$('#scenForm').value,notes:$('#scenNotes').value.trim(),created_by:'Daniel Lacouture (app)',
    moves:SCEN_MOVES.filter(m=>m.player_id).map(m=>({player_id:m.player_id,action:m.action||'keep',
      adjusted_wage:isNaN(m.adjusted_wage)?null:m.adjusted_wage,adjusted_value:isNaN(m.adjusted_value)?null:m.adjusted_value,note:m.note||null}))};
  msg.textContent='Saving to Lakebase…';$('#scenSaveBtn').disabled=true;
  try{const saved=await api('/api/scenario',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    scenClose();ACTIVE=saved.scenario_id;await initScenarios();
  }catch(e){msg.textContent=e.message;$('#scenSaveBtn').disabled=false;}
}

/* ---------------- PLAYER MODAL ---------------- */
async function openPlayer(id){
  $('#modal').classList.add('open');
  $('#pcard').innerHTML='<div class="body" style="padding:48px;text-align:center"><span class="spin"></span></div>';
  try{
    const [{player:p,scout_reports:reps},tf]=await Promise.all([
      api('/api/player/'+id), api('/api/transfer/'+id).catch(()=>null)]);
    const foot=h32(p.player_id)%3===0?'Left':'Right';
    const pos0=p.positions.split(',')[0].trim();
    const tags=[];
    if(['ST','RW','LW'].includes(pos0))tags.push('POWER FORWARD'); if(pos0==='CB'||pos0==='DM')tags.push('BALL-PLAYER');
    if(+p.gpv> +p.est_valuation_low)tags.push('UNDERVALUED'); if(p.age<=21)tags.push('HIGH CEILING');
    if(p.status==='Key Player'||p.status==='Captain')tags.push('KEY PLAYER');
    const G=Number(p.gpr)||70;
    const clamp=v=>Math.max(42,Math.min(99,Math.round(v)));
    const carry=clamp(G+rnd(p.player_id+'c',-6,8));
    const drib=clamp(G+rnd(p.player_id+'d',-8,7));
    const pass=clamp(G+rnd(p.player_id+'p',-7,6));
    const shoot=clamp(G+rnd(p.player_id+'s',-14,6));
    const phys=clamp(G+rnd(p.player_id+'ph',-10,9));
    const press=Math.round(rnd(p.player_id+'ap',68,95));
    const rep=reps&&reps[0];
    $('#pcard').innerHTML=`
      <div class="hero"><span class="close" onclick="closeModal()">×</span>
        <div class="big"><img class="hs" src="/static/headshots/${p.player_id}.jpg" alt="${p.name}" onerror="this.parentNode.textContent='${initials(p.name)}'"></div>
        <div><h2>${p.name}</h2><div class="meta">${pos0} · ${p.club} · ${p.age}y · ${foot} foot · ${p.nationality}</div>
          <div class="tags">${(INJ_BY[p.player_id]?[`<span class="availpill ${availCls(INJ_BY[p.player_id].availability)}" title="Load risk ${(+INJ_BY[p.player_id].risk_score).toFixed(0)} · ${INJ_BY[p.player_id].risk_band}">● ${INJ_BY[p.player_id].availability}</span>`]:[]).concat(tags.slice(0,2).map(t=>`<span class="pill ${t==='UNDERVALUED'?'green':'blue'}">${t}</span>`)).join('')}</div></div></div>
      <div class="body">
        <div class="custommetric"><div><div class="cl">ARSENAL PRESSING INDEX</div><div style="font-size:11px;opacity:.7;margin-top:2px">Fit to our high-press model</div></div><div class="cv">${press}</div></div>
        <div class="trirow">
          <div class="tri"><div class="v">${p.gpr}</div><div class="k">ACME PLAYER RATING</div></div>
          <div class="tri"><div class="v">${p.player_style_fit}</div><div class="k">PLAYER STYLE FIT</div></div>
          <div class="tri"><div class="v">${p.team_style_fit}</div><div class="k">TEAM STYLE FIT</div></div></div>
        <div class="statgrid">
          <div class="stat"><div class="l">Transfer value range</div><div class="v">${eM(p.est_valuation_low)} – ${eM(p.est_valuation_high)}</div></div>
          <div class="stat"><div class="l">Months remaining</div><div class="v">${p.months_left}</div></div>
          <div class="stat"><div class="l">Release clause</div><div class="v">${eM(p.release_clause)}</div></div>
          <div class="stat"><div class="l">Current season GPR</div><div class="v">${p.gpr}</div></div></div>
        ${tfEntry(tf)}
        <div class="skills">
          ${skill('Carrying',carry)}${skill('Dribbling',drib)}${skill('Passing',pass)}${skill('Shooting',shoot)}
          <div class="skill"><div class="l">Physical score<b>${phys}</b></div><div class="bar amber"><i style="width:${phys}%"></i></div></div>
        </div>
        ${rep?`<div class="reportbox"><div class="rh"><span>${rep.scout_name}</span><span>${rep.report_date} · ${rep.status}</span></div><div class="rs">${rep.summary}</div></div>`:''}
      </div>`;
  }catch(e){$('#pcard').innerHTML=`<div class="body">Error: ${e.message}</div>`;}
}
const skill=(l,v)=>`<div class="skill"><div class="l">${l}<b>${v}</b></div><div class="bar"><i style="width:${v}%"></i></div></div>`;
/* Compact valuation card in the player modal — an ENTRY POINT into the full
   interactive AI Transfer Assistant (replaces the old static waterfall). */
function tfEntry(tf){
  if(!tf||!tf.valuation)return '';
  const v=tf.valuation, live=/acme-transfer-valuation/.test(tf.source||'');
  const tops=(v.top_drivers||[]).slice(0,3);
  return `<div class="valcard tf-entry" onclick="location.hash='agents/transfer/${tf.player_id}';closeModal()">
    <div class="valh"><div><div class="cl">AI TRANSFER VALUATION</div>
      <div class="vsub">${tf.group_label} model · ${live?'Model Serving':'calibrated (local)'}</div></div>
      <div class="valv">${eMv(v.value)}</div></div>
    <div class="valnote">Position-specific drivers, recomputed live. Top factors right now:</div>
    <div class="tf-entry-drivers">${tops.map(d=>`<span class="tf-chip ${d.contribution>=0?'up':'down'}">${d.label} ${dM(d.contribution)}</span>`).join('')}</div>
    <div class="tf-entry-cta">Open the interactive valuation — adjust KPIs &amp; watch value move <span>→</span></div>
  </div>`;
}
function closeModal(){$('#modal').classList.remove('open');if(location.hash.startsWith('#player'))history.replaceState(null,'','#squad');}
$('#modal').onclick=e=>{if(e.target.id==='modal')closeModal();};

/* ---------------- ASK (live Acme Scout agent — Genie One style) ---------------- */
// [short chip label, full question sent to the agent]
const ASK_Q=[
  ["Highest-rated players & value","Who are our highest-rated players and what are they worth?"],
  ["Contracts expiring soonest","Which of our first-team players have the least time left on their contracts?"],
  ["Saka's release clause","What does Bukayo Saka's contract say about his release clause and end date?"],
  ["Latest scout note: Vitor Roque","Summarize the latest scout note on Vitor Roque"],
];
const GEM_ICON='<svg viewBox="0 0 24 24" fill="currentColor" stroke="none"><path d="M12 2c.7 5.3 2 6.6 7.3 7.3C14 10 12.7 11.3 12 16.7 11.3 11.3 10 10 4.7 9.3 10 8.6 11.3 7.3 12 2z"/></svg>';
if($('#askSuggest')){
  $('#askSuggest').innerHTML=ASK_Q.map(([label])=>`<button class="gask-chip">${GEM_ICON}${label}</button>`).join('');
  $$('#askSuggest .gask-chip').forEach((el,i)=>el.onclick=()=>{const q=ASK_Q[i][1];$('#askInput').value=q;runAsk(q);});
}
// rotating grey suggestion in the input (Genie One-style), Tab to accept
let askRotIdx=0, askRotTimer=null;
function askShowRot(){const ph=$('#gaskPhText');if(!ph)return;
  const empty=!($('#askInput')&&$('#askInput').value.trim());
  const box=$('#gaskPh'); if(box)box.style.display=empty?'flex':'none';
  if(empty)ph.textContent=ASK_Q[askRotIdx][1];}
function askStartRot(){if(askRotTimer)return;askShowRot();
  askRotTimer=setInterval(()=>{askRotIdx=(askRotIdx+1)%ASK_Q.length;askShowRot();},3800);}
function askStopRot(){if(askRotTimer){clearInterval(askRotTimer);askRotTimer=null;}}
if($('#askInput')){
  $('#askInput').addEventListener('input',askShowRot);
  $('#askInput').addEventListener('keydown',e=>{
    if(e.key==='Tab' && !$('#askInput').value.trim()){e.preventDefault();$('#askInput').value=ASK_Q[askRotIdx][1];askShowRot();$('#askInput').focus();}
  });
}
// XSS-safe markdown -> HTML for Genie answers (headers, tables, bold, links, code)
function askInline(t){
  t=t.replace(/\\([\[\]])/g,'$1');                                             // unescape \[ \]
  t=t.replace(/\[([^\]]*)\]\((https?:[^)\s]+)\)/g,'<a href="$2" target="_blank" rel="noopener">$1</a>');
  t=t.replace(/\*\*([^*]+)\*\*/g,'<b>$1</b>');
  t=t.replace(/`([^`]+)`/g,'<code>$1</code>');
  return t;
}
function askMd(s){
  const esc=(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  const lines=esc.split('\n'); const out=[]; let i=0, para=[];
  const flush=()=>{ if(para.length){out.push('<p>'+askInline(para.join('<br>'))+'</p>');para=[];} };
  const isRow=l=>/^\s*\|.*\|\s*$/.test(l);
  const isSep=l=>/^\s*\|(\s*:?-{2,}:?\s*\|)+\s*$/.test(l);
  const cells=l=>l.trim().replace(/^\||\|$/g,'').split('|').map(c=>c.trim());
  while(i<lines.length){
    const l=lines[i];
    if(isRow(l) && i+1<lines.length && isSep(lines[i+1])){          // markdown table
      flush();
      const head=cells(l); i+=2; const body=[];
      while(i<lines.length && isRow(lines[i])){body.push(cells(lines[i]));i++;}
      out.push('<div class="ask-tw"><table class="ask-tbl"><thead><tr>'+
        head.map(h=>`<th>${askInline(h)}</th>`).join('')+'</tr></thead><tbody>'+
        body.map(r=>'<tr>'+r.map(c=>`<td>${askInline(c)}</td>`).join('')+'</tr>').join('')+
        '</tbody></table></div>');
      continue;
    }
    const h=l.match(/^\s*(#{1,4})\s+(.*)$/);
    if(h){ flush(); const lv=Math.min(4,h[1].length+2); out.push(`<h${lv} class="ask-h">${askInline(h[2])}</h${lv}>`); i++; continue; }
    if(l.trim()===''){ flush(); i++; continue; }
    para.push(l); i++;
  }
  flush();
  return out.join('');
}
let asking=false;
const escHtml=s=>(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
async function runAsk(q){
  if(!q||asking)return;asking=true;
  const btn=$('#askBtn'),box=$('#askResult');if(btn){btn.disabled=true;}
  askShowRot();
  box.innerHTML=`<div class="ask-thread"><div class="ask-q">${escHtml(q)}</div>
    <div class="ask-loading"><span class="spin"></span> Acme Scout is reasoning over your squad tables, contracts &amp; scout notes…</div></div>`;
  box.scrollIntoView({behavior:'smooth',block:'start'});
  try{
    const r=await api('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q})});
    const body=r.answer
      ? `<div class="ask-answer"><div class="ask-a-h"><span class="dbx-dot"></span> Acme Scout · Agent mode · blended over tables + documents</div>
          <div class="ask-a-body">${askMd(r.answer)}</div></div>`
      : `<div class="status err" style="display:block">Couldn't get an answer${r.error?': '+(typeof r.error==='string'?r.error:JSON.stringify(r.error)).slice(0,200):''}.</div>`;
    box.innerHTML=`<div class="ask-thread"><div class="ask-q">${escHtml(q)}</div>${body}</div>`;
  }catch(e){box.innerHTML=`<div class="ask-thread"><div class="ask-q">${escHtml(q)}</div><div class="status err" style="display:block">${e.message}</div></div>`;}
  asking=false;if(btn){btn.disabled=false;}
}
$('#askBtn')&&($('#askBtn').onclick=()=>runAsk($('#askInput').value.trim()));
$('#askInput')&&$('#askInput').addEventListener('keydown',e=>{if(e.key==='Enter')runAsk($('#askInput').value.trim());});

/* ---------------- CLIP SEARCH ---------------- */
let clipping=false;
// Check media_type first (new schema), fallback to file extension (legacy)
const isVid=c=>(c.media_type==='video') || (c.media_type!=='image' && /\.mp4$/i.test(c.file||''));
const clipMedia=c=>isVid(c)
  ? `<video class="clipvid" controls preload="metadata" playsinline muted poster="/api/clip/image/${c.clip_id}"><source src="/api/clip/video/${c.clip_id}" type="video/mp4"></video><span class="vidbadge">VIDEO</span>`
  : `<img loading="lazy" src="/api/clip/image/${c.clip_id}" alt="${c.name}"/>`;
const capHtml=c=>{const m=(c.caption||'').match(/^\[([^\]]+)\]\s*(.*)$/);
  return m?`<span class="frmchip">${m[1]}</span> ${m[2]}`:c.caption;};
const frameCount=c=>{const m=(c.caption||'').match(/(\d+)\s*frames?\s*sampled/i);return m?Math.min(+m[1],6):4;};
const filmstrip=c=>{if(!isVid(c))return'';let s='';for(let i=1;i<=frameCount(c);i++)s+=`<img loading="lazy" src="/api/clip/frame/${c.clip_id}/${i}" onerror="this.remove()"/>`;
  return `<div class="filmstrip" title="The actual frames sampled from this clip and captioned by the vision model"><span class="fs-l">🎞 frames the vision model read</span><div class="fs-imgs">${s}</div></div>`;};
const clipCard=(c,scene)=>`<div class="clipcard"><div class="imgwrap">${clipMedia(c)}${scene?`<span class="score">${(c.score*100).toFixed(0)}%</span>`:''}</div><div class="meta">${scene?`<div class="n">${c.name}</div><div class="c">${c.club}</div>`:''}<div class="cap">${capHtml(c)}</div>${filmstrip(c)}</div></div>`;
async function runClip(q){
  if(!q||clipping)return;clipping=true;const box=$('#clipResults');
  box.innerHTML='<div class="cliploading"><span class="spin"></span> Searching scouting clips…</div>';
  try{
    const r=await api('/api/clip/search?q='+encodeURIComponent(q));
    if(r.mode==='player'){const p=r.player;
      box.innerHTML=`<div class="playerhead"><div class="phbadge">${initials(p.name)}</div>
        <div><div class="phname">${p.name}</div><div class="phclub">${p.club}</div></div>
        <div class="phright"><span class="matchpill">Resolved · ${(p.score*100).toFixed(0)}% match</span><span class="phcount">${r.clips.length} clip${r.clips.length>1?'s':''}</span></div></div>
        <div class="clipgrid">${r.clips.map(c=>clipCard(c,false)).join('')}</div>`;
    }else if(r.mode==='club'){const cl=r.club;
      box.innerHTML=`<div class="playerhead"><div class="phbadge">${initials(cl.name)}</div>
        <div><div class="phname">${cl.name}</div><div class="phclub">${cl.players} players · club gallery</div></div>
        <div class="phright"><span class="matchpill">Resolved club</span><span class="phcount">${cl.count} clips</span></div></div>
        <div class="clipgrid">${r.clips.map(c=>clipCard(c,true)).join('')}</div>`;
    }else{
      box.innerHTML=`<div class="scenehint">No single player matched — showing best clips across players for “${q}”.</div><div class="clipgrid">${r.clips.map(c=>clipCard(c,true)).join('')}</div>`;
    }
  }catch(e){box.innerHTML=`<div class="status err" style="display:block">${e.message}</div>`;}
  clipping=false;
}
$('#clipBtn').onclick=()=>runClip($('#clipInput').value.trim());
$('#clipInput').addEventListener('keydown',e=>{if(e.key==='Enter')$('#clipBtn').click();});

/* ---------------- AI PHYSIO / LOAD MANAGER ---------------- */
let PHYSIO=[], physioLoaded=false;
const flagCls=f=>({Red:'red',Amber:'amber',Green:'green'}[f]||'');
function spark(vals,color,h=34){
  if(!vals||!vals.length)return '';
  const w=180,mx=Math.max(...vals,1),mn=Math.min(...vals,0),rng=(mx-mn)||1;
  const pts=vals.map((v,i)=>`${(i/(vals.length-1||1))*w},${h-2-((v-mn)/rng)*(h-4)}`).join(' ');
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none"><polyline points="${pts}" fill="none" stroke="${color}" stroke-width="2"/></svg>`;
}
async function loadPhysio(sub){
  const tbl=$('#physioTable');
  if(!physioLoaded){
    try{ PHYSIO=await api('/api/physio'); physioLoaded=true; }
    catch(e){ tbl.innerHTML=`<tr><td>Load failed: ${e.message}</td></tr>`; return; }
  }
  const n=f=>PHYSIO.filter(p=>p.load_flag===f).length;
  $('#physioStrip').innerHTML=[['Red','Rest / cap minutes'],['Amber','Monitor'],['Green','Full availability']]
    .map(([f,l])=>`<div class="pill-stat ${flagCls(f)}"><b>${n(f)}</b><span>${l}</span></div>`).join('');
  tbl.innerHTML=`<thead><tr><th>PLAYER</th><th>ACWR</th><th>7d MIN</th><th>REC%</th><th>SLEEP</th><th>INJURY</th><th>NEXT</th></tr></thead><tbody>`+
    PHYSIO.map(p=>`<tr data-pid="${p.player_id}" class="physio-row">
      <td><div class="pname"><span class="dot ${flagCls(p.load_flag)}"></span><span class="pmini">${initials(p.player_name)}</span>${p.player_name}<span class="muted" style="margin-left:6px;font-size:11px">${p.positions}</span></div></td>
      <td><b class="${p.acwr>1.3?'hot':''}">${p.acwr}</b></td>
      <td>${p.match_minutes_7d}'</td>
      <td>${p.avg_recovery_7d}%</td>
      <td>${p.avg_sleep_7d}h</td>
      <td><span class="pill ${bandCls(p.injury_band)}">${p.injury_band}</span></td>
      <td><b>${p.recommended_minutes_next}'</b></td></tr>`).join('')+`</tbody>`;
  $$('#physioTable .physio-row').forEach(r=>r.onclick=()=>{location.hash='agents/physio/'+r.dataset.pid;});
  const pid=sub||(PHYSIO[0]&&PHYSIO[0].player_id);
  if(pid){ $$('#physioTable .physio-row').forEach(r=>r.classList.toggle('sel',r.dataset.pid===pid)); openPhysio(pid); }
}
async function openPhysio(pid){
  const box=$('#physioDetail');
  box.innerHTML=`<div class="physio-empty">Loading…</div>`;
  let d; try{ d=await api('/api/physio/'+pid); }catch(e){ box.innerHTML=`<div class="physio-empty">${e.message}</div>`; return; }
  const s=d.status;
  const loadVals=(d.sessions||[]).map(x=>+x.player_load);
  const recVals=(d.recovery||[]).map(x=>+x.recovery_pct);
  box.innerHTML=`
    <div class="card-h"><div><h3>${s.player_name} <span class="pill ${flagCls(s.load_flag)}" style="margin-left:6px">${s.load_flag}</span></h3>
      <div class="sub">${s.positions} · age ${s.age} · injury risk ${s.injury_band}</div></div>
      <div class="rec-badge"><div class="n">${s.recommended_minutes_next}'</div><div class="k">RECOMMENDED NEXT</div></div></div>
    <div class="mini4">
      <div class="m"><div class="n ${s.acwr>1.3?'hot':''}">${s.acwr}</div><div class="k">ACWR (>1.3 spike)</div></div>
      <div class="m"><div class="n">${s.match_minutes_7d}'</div><div class="k">MINUTES 7D</div></div>
      <div class="m"><div class="n">${s.avg_recovery_7d}%</div><div class="k">WHOOP RECOVERY 7D</div></div>
      <div class="m"><div class="n">${s.avg_sleep_7d}h</div><div class="k">SLEEP 7D</div></div></div>
    <div class="trend"><div class="l">GPS player-load (14d) <span>${s.distance_7d_km} km last 7d</span></div>${spark(loadVals,'#2563EB')}</div>
    <div class="trend"><div class="l">Whoop recovery (14d) <span>HRV ${s.hrv_recent_ms}ms</span></div>${spark(recVals,'#16A34A')}</div>
    ${gpsPanel(d.gps_metrics)}
    <div class="rec-box" id="recBox"><div class="rec-h"><svg viewBox="0 0 24 24"><path d="M12 3l1.9 4.9L19 9.8l-4 3.6 1 5.2L12 16l-4 2.6 1-5.2-4-3.6 5.1-1.9z"/></svg> AI physio recommendation</div>
      <label class="ptn-l">Physio team notes <span class="muted" style="font-weight:500">— optional; folded into the recommendation</span></label>
      <textarea id="physioNote" class="ptn" placeholder="e.g. Tightness in the left hamstring reported after training — prefer a 60-minute cap and no sprint work in the warm-up."></textarea>
      <button class="askbtn" id="recBtn2">Generate recommendation</button></div>`;
  $('#recBtn2').onclick=async()=>{
    const note=($('#physioNote')&&$('#physioNote').value.trim())||'';
    const rb=$('#recBox'); rb.querySelector('#recBtn2').outerHTML=`<div class="status work" style="display:block">Analysing load, GPS strain &amp; recovery…</div>`;
    try{ const r=await api('/api/physio/'+pid+'/recommend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({note:note||null})});
      const used=r.used_team_note?`<span class="pill green" style="margin-left:8px">team note folded in</span>`:'';
      rb.querySelector('.status').outerHTML=`<div class="rec-text">${r.recommendation}${used}</div><div class="rec-src">${r.source}</div>`;
    }catch(e){ rb.querySelector('.status').outerHTML=`<div class="status err" style="display:block">${e.message}</div>`; }
  };
}
function gpsPanel(g){
  if(!g)return '';
  const t=(v,k,cls)=>`<div class="gps-tile ${cls||''}"><div class="v">${v}</div><div class="k">${k}</div></div>`;
  const sd=Number(g.strain_delta_pct);
  return `<div class="section-h" style="margin-top:18px">STATSports GPS-vest · last match
      <span class="muted" style="text-transform:none;font-weight:500;letter-spacing:0">— ${g.last_match_minutes}′ played · season avg ${g.season_avg_minutes}′</span></div>
    <div class="gps-grid">
      ${t((g.total_distance_m/1000).toFixed(1)+'<em>km</em>','Total distance')}
      ${t(g.hsr_distance_m+'<em>m</em>','High-speed running')}
      ${t(g.sprint_distance_m+'<em>m</em>','Sprint distance')}
      ${t(g.sprint_count,'Sprints')}
      ${t(g.accel_count+' / '+g.decel_count,'Accel / decel')}
      ${t(g.dynamic_stress_load,'Dynamic Stress Load')}
      ${t(g.player_load,'Player load')}
      ${t(g.hml_distance_m+'<em>m</em>','High-metabolic-load dist')}
      ${t(g.top_speed_kmh+'<em>km/h</em>','Top speed')}
      ${t((sd>=0?'+':'−')+Math.abs(sd)+'<em>%</em>','Strain vs last match',sd>=0?'up':'down')}
      ${t('#'+g.load_rank+'<em>of '+g.squad_n+'</em>','Cumulative load rank')}
      ${t(g.load_percentile+'<em>pctile</em>','Load vs peers')}
    </div>`;
}

/* ---------------- AI TRANSFER ASSISTANT ---------------- */
let TF=null, tfInit=false;
const tfFmt=(v,d)=>Number(v).toFixed(d);
function tfScore(){
  let total=TF.base;const contribs=[];
  for(const s of TF.sliders){
    const x=+s.value, xeff=s.key==='age'?Math.max(x,19):x;
    const c=s.coef*(xeff-s.ref);
    contribs.push({key:s.key,label:s.label,contribution:c});
    total+=c;
  }
  total=Math.max(3,Math.min(250,total));
  return {value:Math.round(total*10)/10, base:TF.base, contribs};
}
function tfSliderHtml(s){
  return `<div class="tf-slider" data-key="${s.key}">
    <div class="tf-sl-top"><span class="tf-sl-l">${s.label}</span><span class="tf-sl-v"><b id="tfv-${s.key}">${tfFmt(s.value,s.decimals)}</b><em>${s.unit}</em></span></div>
    <input type="range" min="${s.min}" max="${s.max}" step="${s.decimals?1/Math.pow(10,s.decimals):1}" value="${s.value}" data-key="${s.key}"/>
    <div class="tf-sl-scale"><span>${s.min}</span><span class="tf-sl-ref" title="peer reference">ref ${tfFmt(s.ref,s.decimals)}</span><span>${s.max}</span></div>
  </div>`;
}
function renderTfValue(res){
  // res (optional) = endpoint response {value, base, contributions}; else local calibrated math
  const r=res?{value:res.value,base:res.base,contribs:res.contributions||res.contribs}:tfScore();
  const vEl=$('#tfValue');
  vEl.textContent=eMv(r.value);
  if(res){vEl.classList.remove('flash');void vEl.offsetWidth;vEl.classList.add('flash');}
  $('#tfValueSub').innerHTML=`Peer base ${eMv(r.base)} · ${TF.group_label}`;
  // bridge: drivers sorted by |impact|, signed bars from a centre line
  const drivers=r.contribs.filter(c=>true).sort((a,b)=>Math.abs(b.contribution)-Math.abs(a.contribution));
  const mx=Math.max(1,...drivers.map(d=>Math.abs(d.contribution)));
  $('#tfBridge').innerHTML=
    `<div class="tf-brow tf-base"><span class="tf-bl">Peer baseline</span><div class="tf-btrack"></div><span class="tf-bd">${eMv(r.base)}</span></div>`+
    drivers.map(d=>{const up=d.contribution>=0,w=Math.abs(d.contribution)/mx*50;
      return `<div class="tf-brow"><span class="tf-bl">${d.label}</span>
        <div class="tf-btrack"><span class="tf-mid"></span><i class="tf-bseg ${up?'up':'down'}" style="${up?`left:50%;width:${w}%`:`right:50%;width:${w}%`}"></i></div>
        <span class="tf-bd ${up?'up':'down'}">${dM(d.contribution)}</span></div>`;}).join('')+
    `<div class="tf-brow tf-final"><span class="tf-bl">Modelled value</span><div class="tf-btrack"></div><span class="tf-bd">= ${eMv(r.value)}</span></div>`;
}
function wireTfSliders(){
  $$('#sub-transfer input[type=range]').forEach(inp=>{
    inp.oninput=()=>{const k=inp.dataset.key;const s=TF.sliders.find(x=>x.key===k);
      s.value=+inp.value; $('#tfv-'+k).textContent=tfFmt(s.value,s.decimals); renderTfValue();
      $('#tfSource').textContent='● live (local recompute)';$('#tfSource').className='tf-src local';};
  });
}
async function loadTransfer(pid){
  if(!tfInit){
    const opts=SQUAD.filter(p=>p.tier!=='Academy'||['p_dowman','p_roque'].includes(p.player_id));
    $('#tfPlayer').innerHTML=SQUAD.map(p=>`<option value="${p.player_id}">${p.name} · ${p.positions.split(',')[0]}</option>`).join('');
    $('#tfPlayer').onchange=()=>{location.hash='agents/transfer/'+$('#tfPlayer').value;};
    $('#tfReset').onclick=()=>openTransfer(TF&&TF.player_id,true);
    tfInit=true;
  }
  const target=pid||(TF&&TF.player_id)||($('#tfPlayer').value)||(SQUAD[0]&&SQUAD[0].player_id);
  if(target)openTransfer(target);
}
async function openTransfer(pid,forceReload){
  if(!pid)return;
  if($('#tfPlayer').value!==pid)$('#tfPlayer').value=pid;
  $('#tfValue').textContent='…';$('#tfBridge').innerHTML='';
  let d; try{ d=await api('/api/transfer/'+pid); }
  catch(e){ $('#tfValue').textContent='—'; $('#tfBridge').innerHTML=`<div class="status err" style="display:block">${e.message}</div>`; return; }
  TF={player_id:pid, group:d.group, group_label:d.group_label, base:d.base, sliders:d.sliders.map(s=>({...s}))};
  $('#tfGroup').textContent=d.group_label;
  const live=/acme-transfer-valuation/.test(d.source||'');
  $('#tfSource').textContent=live?'Model Serving · acme-transfer-valuation':'● calibrated model (local)';
  $('#tfSource').className='tf-src '+(live?'live':'local');
  $('#tfUniversal').innerHTML=TF.sliders.filter(s=>s.universal).map(tfSliderHtml).join('');
  $('#tfPosHdr').textContent=d.group_label+' performance drivers';
  $('#tfPosition').innerHTML=TF.sliders.filter(s=>!s.universal).map(tfSliderHtml).join('');
  wireTfSliders(); renderTfValue();
}
$('#tfRecompute')&&($('#tfRecompute').onclick=async()=>{
  if(!TF)return;const btn=$('#tfRecompute');const old=btn.textContent;btn.textContent='Scoring on endpoint…';btn.disabled=true;
  const values={};TF.sliders.forEach(s=>values[s.key]=+s.value);
  try{const r=await api('/api/transfer/value',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({group:TF.group,values})});
    const live=/acme-transfer-valuation/.test(r.source||'');
    $('#tfSource').textContent=live?'Model Serving · acme-transfer-valuation':'● calibrated model (local fallback)';
    $('#tfSource').className='tf-src '+(live?'live':'local');
    // repaint the FULL breakdown from the endpoint response (value + bridge), with a flash
    renderTfValue(r.valuation);
    const t=new Date().toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
    $('#tfValueSub').innerHTML=`Peer base ${eMv(r.valuation.base)} · ${TF.group_label} · <span class="tf-scored">${live?'scored on Model Serving':'scored locally'} ${t}</span>`;
    btn.textContent=live?'✓ Scored on Model Serving':'✓ Recomputed (local)';
    setTimeout(()=>{btn.textContent=old;btn.disabled=false;},1600);return;
  }catch(e){$('#tfSource').textContent='endpoint error';}
  btn.textContent=old;btn.disabled=false;});

/* ---------------- AI NUTRITION ASSISTANT ---------------- */
let NT=null, ntInit=false, ntRec=null, ntRecording=false;
function loadNutrition(pid){
  if(!ntInit){
    $('#ntPlayer').innerHTML=SQUAD.map(p=>`<option value="${p.player_id}">${p.name} · ${p.positions.split(',')[0]}</option>`).join('');
    $('#ntPlayer').onchange=()=>{location.hash='agents/nutrition/'+$('#ntPlayer').value;};
    wireNtVoice(); $('#ntGenBtn').onclick=ntGenerate; ntInit=true;
  }
  const target=pid||(NT&&NT.player_id)||$('#ntPlayer').value||(SQUAD[0]&&SQUAD[0].player_id);
  if(target)openNutrition(target);
}
async function openNutrition(pid){
  if($('#ntPlayer').value!==pid)$('#ntPlayer').value=pid;
  let m; try{ m=await api('/api/nutrition/'+pid); }
  catch(e){ $('#ntMetrics').innerHTML=`<div class="status err" style="display:block">${e.message}</div>`; return; }
  NT={player_id:pid, name:m.player_name};
  $('#ntGroup').textContent=m.positions;
  $('#ntSource').textContent='● ready';$('#ntSource').className='tf-src local';
  const flagc=({Red:'red',Amber:'amber',Green:'green'}[m.load_flag]||'');
  $('#ntMetrics').innerHTML=[
    ['DISTANCE 7D',m.distance_7d_km+' km'],['SLEEP 7D',m.avg_sleep_7d+'h'],
    ['RECOVERY 7D',m.avg_recovery_7d+'%'],['NEXT MATCH',m.recommended_minutes_next+"'"],
    ['EST. DAILY ENERGY','~'+m.est_daily_kcal+' kcal'],['LOAD FLAG',`<span class="pill ${flagc}">${m.load_flag}</span>`]
  ].map(([k,v])=>`<div class="nt-tile"><div class="v">${v}</div><div class="k">${k}</div></div>`).join('');
  $('#ntOutput').innerHTML=`<div class="nt-empty">Add an optional voice note, then <b>Generate fuelling plan</b> for ${m.player_name}.</div>`;
}
function wireNtVoice(){
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  $('#ntRecBtn').onclick=()=>{
    if(ntRecording){try{ntRec&&ntRec.stop();}catch(e){}return;}
    if(!SR){$('#ntNote').placeholder='(Live transcription not supported here — type your note.)';return;}
    ntRec=new SR();ntRec.continuous=true;ntRec.interimResults=true;ntRec.lang='en-GB';
    const base=$('#ntNote').value?($('#ntNote').value+' '):'';
    ntRec.onresult=e=>{let t='';for(const r of e.results)t+=r[0].transcript;$('#ntNote').value=base+t;};
    ntRec.onend=()=>{ntRecording=false;$('#ntRecBtn').textContent='● Record note';$('#ntRecBtn').classList.remove('on');};
    ntRec.start();ntRecording=true;$('#ntRecBtn').textContent='■ Stop';$('#ntRecBtn').classList.add('on');
  };
}
async function ntGenerate(){
  if(!NT)return;const out=$('#ntOutput');const btn=$('#ntGenBtn');
  const note=$('#ntNote').value.trim();
  out.innerHTML=`<div class="nt-loading"><span class="spin"></span> Generating tailored fuelling plan…</div>`;
  btn.disabled=true;$('#ntSource').textContent='● ai_query…';$('#ntSource').className='tf-src local';
  try{
    const r=await api('/api/nutrition/'+NT.player_id+'/recommend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({note:note||null})});
    $('#ntSource').textContent=(r.source||'ai_query');$('#ntSource').className='tf-src live';
    out.innerHTML=ntPlanHtml(r);
    typewrite(out.querySelector('.nt-summary'));
  }catch(e){out.innerHTML=`<div class="status err" style="display:block">${e.message}</div>`;}
  btn.disabled=false;
}
function ntPlanHtml(r){
  const b=r.baseline, a=r.adjustments;
  const voice=r.used_voice_note?`<span class="pill green" style="margin-left:8px">voice note used</span>`:'';
  if(!b)return `<div class="card-h"><div><h3>Fuelling plan — ${r.player_name}</h3></div></div><div class="nt-plan-raw">${(r.raw||'').replace(/</g,'&lt;')}</div>`;
  const macro=(lbl,base,adj,u)=>{u=u||'';
    const changed=(adj!=null && Number(adj)!==Number(base));
    const chg=changed?`<span class="nt-delta ${Number(adj)>Number(base)?'up':'down'}">→ ${adj}${u}</span>`:'';
    return `<div class="nt-macro"><div class="v">${base}<em>${u}</em>${chg}</div><div class="k">${lbl}${changed?' · adjusted':''}</div></div>`;};
  const row=(lbl,v)=>v?`<div class="nt-row"><div><div class="nt-l">${lbl}</div><div class="nt-v">${v}</div></div></div>`:'';
  const items=(a&&a.adjustments)||[];
  const adjHtml=items.length?`<div class="section-h" style="margin-top:18px">What to adjust <span class="muted" style="text-transform:none;font-weight:500;letter-spacing:0">— vs baseline</span></div>
    <div class="nt-adjs">${items.map(x=>`<div class="nt-adj"><div class="nt-adj-h"><span class="nt-adj-item">${x.item||''}</span><span class="nt-adj-change">${x.change||''}</span></div><div class="nt-adj-why">${x.why||''}</div></div>`).join('')}</div>
    ${a&&a.summary?`<div class="nt-summary">${a.summary}</div>`:''}`
    :`<div class="nt-summary" style="margin-top:16px">${(a&&a.summary)||'No adjustments needed — hold the baseline plan.'}</div>`;
  return `<div class="card-h"><div><h3>Fuelling — ${r.player_name}${voice}</h3><div class="sub">Baseline plan + AI adjustments, grounded in live load, sleep &amp; recovery</div></div></div>
    <div class="nt-baseline-l">Baseline plan</div>
    <div class="nt-macros">${macro('Daily energy',b.daily_kcal,a&&a.adjusted_kcal,'')}${macro('Carbs',b.carbs_g,a&&a.adjusted_carbs_g,'g')}${macro('Protein',b.protein_g,a&&a.adjusted_protein_g,'g')}</div>
    <div class="nt-rows">
      ${row('Hydration',b.hydration_l+' L/day')}
      ${row('Pre-match',b.pre_match)}
      ${row('Matchday',b.matchday)}
      ${row('Recovery',b.recovery)}
    </div>
    ${adjHtml}`;
}

/* ---------------- AI OPPOSITION / MATCH-PREP ANALYST ---------------- */
let OPP=[], OPP_ACTIVE=null, oppLoaded=false;
async function loadOpposition(sub){
  if(!oppLoaded){
    try{ OPP=await api('/api/opposition'); oppLoaded=true; }
    catch(e){ $('#opPicker').innerHTML=`<div class="status err" style="display:block">${e.message}</div>`; return; }
  }
  $('#opPicker').innerHTML=OPP.map(o=>`<div class="op-card ${o.opponent_id===OPP_ACTIVE?'active':''}" data-id="${o.opponent_id}">
    <div class="op-crest">${initials(o.opponent)}</div>
    <div class="op-cbody"><div class="op-cname">${o.opponent}</div>
      <div class="op-cmeta">${o.competition} · ${o.venue} · ${o.match_date}</div>
      <div class="op-cform">${o.formation} · ${o.play_style}</div></div></div>`).join('');
  $$('#opPicker .op-card').forEach(c=>c.onclick=()=>{location.hash='agents/coach/'+c.dataset.id;});
  const pick=sub||OPP_ACTIVE||(OPP[0]&&OPP[0].opponent_id);
  if(pick)openOpposition(pick);
}
function opMetric(v,l){return `<div class="op-metric"><div class="v">${v}</div><div class="l">${l}</div></div>`;}
async function openOpposition(id){
  OPP_ACTIVE=id;
  $$('#opPicker .op-card').forEach(c=>c.classList.toggle('active',c.dataset.id===id));
  const o=OPP.find(x=>x.opponent_id===id)||{};
  $('#opMeta').innerHTML=`<div class="op-metrics">
    ${opMetric(o.ppda,'PPDA (press)')}${opMetric(o.xg_for_p90,'xG for /90')}${opMetric(o.xg_against_p90,'xG against /90')}
    ${opMetric(o.possession_pct+'%','Possession')}${opMetric(o.high_press_pct+'%','High-press')}${opMetric(o.field_tilt_pct+'%','Field tilt')}</div>`;
  const box=$('#opReport');
  box.innerHTML=`<div class="op-loading"><span class="spin"></span> Analysing ${o.opponent} — generating match-prep brief with clip citations…</div>`;
  let r; try{ r=await api('/api/opposition/'+id+'/report'); }
  catch(e){ box.innerHTML=`<div class="status err" style="display:block">${e.message}</div>`; return; }
  box.innerHTML=opReportHtml(r);
  typewrite(box.querySelector('.op-summary'));
}
function opClipCard(c){
  if(!c)return `<div class="op-cit-missing">No clip on file</div>`;
  const vid=(c.media_type==='video');
  const media=vid
    ? `<video class="op-cit-media" controls preload="metadata" playsinline muted poster="/api/clip/image/${c.clip_id}"><source src="/api/clip/video/${c.clip_id}" type="video/mp4"></video><span class="vidbadge">VIDEO</span>`
    : `<img class="op-cit-media" loading="lazy" src="/api/clip/image/${c.clip_id}" alt="${c.player_name}"/>`;
  return `<div class="op-cit-clip"><div class="op-cit-imgwrap">${media}</div>
    <div class="op-cit-cap">${(c.caption||'').replace(/^\[[^\]]+\]\s*/,'')}</div></div>`;
}
function opReportHtml(r){
  const b=r.brief;
  const cites=r.citations||[];
  if(!b)return `<div class="card"><div class="op-plan-raw">${(r.raw||'').replace(/</g,'&lt;')}</div></div>`;
  const bullets=arr=>`<ul class="op-bullets">${(arr||[]).map(x=>`<li>${x}</li>`).join('')}</ul>`;
  return `<div class="op-report">
    <div class="op-main">
      <div class="card">
        <div class="op-rh"><div><div class="op-tag">MATCH-PREP BRIEF</div><h3>${r.opponent} <span class="muted" style="font-weight:500;font-size:13px">· ${r.formation} · ${r.play_style}</span></h3></div>
          <span class="tf-src live">${r.source}</span></div>
        <div class="op-summary">${b.summary||''}</div>
        <div class="op-cols">
          <div class="op-col danger"><div class="op-col-h">How they hurt us</div>${bullets(b.how_they_hurt_us)}</div>
          <div class="op-col plan"><div class="op-col-h">How we beat them</div>${bullets(b.how_we_beat_them)}</div>
        </div>
        ${b.set_piece?`<div class="op-setpiece"><b>Set pieces:</b> ${b.set_piece}</div>`:''}
      </div>
    </div>
    <div class="op-side">
      <div class="card">
        <div class="op-tag">KEY BATTLE</div>
        <div class="op-keybattle">${b.key_battle||''}</div>
        <div class="op-cit-h">Scouting clips <span class="muted">cited from the film index</span></div>
        ${cites.map(c=>`<div class="op-cit"><div class="op-cit-name">${c.name} <span class="pill blue">${c.pos||''}</span></div>
          <div class="op-cit-threat">${c.threat||''}</div>${opClipCard(c.clip)}</div>`).join('')}
      </div>
    </div>
  </div>`;
}

/* ---------------- AI CONTRACT & FFP/PSR COMPLIANCE AGENT ---------------- */
let ffpLoaded=false;
const verdictCls=v=>({Compliant:'green','Watch':'amber','At risk':'red'}[v]||'blue');
async function loadFfp(){
  if(ffpLoaded)return;
  const kpis=$('#ffpKpis'); kpis.innerHTML='<div class="kpi"><div class="v">…</div></div>';
  let s; try{ s=await api('/api/ffp'); }
  catch(e){ kpis.innerHTML=`<div class="status err" style="display:block">${e.message}</div>`; return; }
  ffpLoaded=true;
  // KPI tiles
  kpis.innerHTML=[
    ['Wage bill',eMv(s.wage_bill)+'/yr',''],['Amortization',eMv(s.amortization)+'/yr',''],
    ['Annual squad cost',eMv(s.squad_cost),'blue'],['Investment headroom',(s.investment_headroom>=0?'+':'')+eMv(s.investment_headroom),s.investment_headroom>=0?'':'red'],
  ].map(([l,v,c])=>`<div class="kpi"><div class="v ${c==='blue'?'blue':''}" style="${c==='red'?'color:var(--red)':''}">${v}</div><div class="l">${l.toUpperCase()}</div></div>`).join('');
  // squad-cost ratio gauge (0..100%, cap at 70)
  const pct=Math.round(s.squad_cost_ratio*100), cap=Math.round(s.assumptions.uefa_limit_pct*100);
  const bar=Math.min(100,pct), capX=cap;
  const gcol=pct<=cap-10?'var(--green)':pct<=cap?'var(--amber)':'var(--red)';
  $('#ffpGauge').innerHTML=`<div class="ffp-gauge">
      <div class="ffp-gtrack"><i style="width:${bar}%;background:${gcol}"></i>
        <span class="ffp-cap" style="left:${capX}%"><em>70% cap</em></span></div>
      <div class="ffp-gnums"><b style="color:${gcol}">${pct}%</b><span>squad-cost ratio · €${s.squad_cost}M of €${s.assumptions.revenue_eur_m}M revenue</span></div>
    </div>`;
  $('#ffpPsr').innerHTML=`<div class="ffp-psr">
    <div class="ffp-psr-row"><span>Projected annual P&L</span><b class="${s.annual_pl>=0?'up':'down'}">${(s.annual_pl>=0?'+':'')+eMv(s.annual_pl)}</b></div>
    <div class="ffp-psr-row"><span>PSR 3-year headroom <em>(vs €${s.assumptions.psr_allowable_loss_eur_m}M allowable loss)</em></span><b class="${s.psr_headroom>=0?'up':'down'}">${(s.psr_headroom>=0?'+':'')+eMv(s.psr_headroom)}</b></div></div>`;
  // flags
  $('#ffpFlags').innerHTML=s.flags.length?s.flags.map(f=>`<div class="ffp-flag ${f.severity}">
      <span class="ffp-fsev">${f.severity}</span>
      <div><div class="ffp-ftype">${f.player} — ${f.type}</div><div class="ffp-fdetail">${f.detail}</div></div></div>`).join('')
    :'<div class="muted" style="font-size:13px;padding:8px">No compliance risks flagged.</div>';
  // player table
  $('#ffpBody').innerHTML=s.players.map(p=>{
    const exp=(+p.remaining_years)<=1.5;
    return `<tr class="clickable" onclick="location.hash='player/${p.player_id}'">
    <td><div class="pname"><span class="pmini">${initials(p.name)}</span>${p.name}</div></td>
    <td class="right">${p.acquisition_fee?eM(p.acquisition_fee):'—'}</td>
    <td class="right">${eM(p.annual_wage)}</td><td class="right">${eM(p.annual_amortization)}</td>
    <td class="right muted">${eM(p.residual_book_value)}</td>
    <td class="right">${(+p.remaining_years).toFixed(1)}${exp?' <span class="pill red">expiring</span>':''}</td>
    <td class="right"><b>${eM(p.annual_squad_cost)}</b></td></tr>`;}).join('');
  // exec verdict (ai_query) — load after the summary paints
  loadFfpBrief();
  loadFfpScenarios();
}
function fwdRow(label,p){
  const hc=p.headroom>=0?'up':'down';
  return `<div class="fwd-row"><span class="fwd-l">${label}</span>
    <span class="fwd-m">ratio ${Math.round(p.ratio*100)}%</span>
    <span class="fwd-hr ${hc}">${(p.headroom>=0?'+':'')+eMv(p.headroom)} headroom</span></div>`;
}
async function loadFfpScenarios(){
  const box=$('#ffpScenarios'); if(!box)return;
  let d; try{ d=await api('/api/ffp/scenarios'); }catch(e){ box.innerHTML=''; return; }
  const hr=v=>(v>=0?'+':'')+eMv(v);
  const u=d.ucl, sg=d.signing, rn=d.renewal;
  box.innerHTML=`<div class="section-h">Forward-looking scenarios <span class="muted" style="text-transform:none;font-weight:500;letter-spacing:0">— illustrative / synthetic, clearly labelled</span></div>
  <div class="fwd-grid">
    <div class="fwd-card">
      <div class="fwd-h">Champions League participation</div>
      <div class="fwd-sub">Revenue uplift from qualifying — broadcast + gate + prize money</div>
      <div class="fwd-rows">${fwdRow('With UCL',u.with_ucl)}${fwdRow('Without UCL',u.without_ucl)}</div>
      <div class="fwd-note">Qualifying swings squad-cost headroom by <b>${hr(u.headroom_swing)}</b> on a <b>+€${u.uplift_eur_m}M</b> revenue uplift.</div>
    </div>
    <div class="fwd-card">
      <div class="fwd-h">New-signing impact</div>
      <div class="fwd-sub">${sg.name} · €${sg.fee_eur_m}M fee · €${sg.wage_eur_m}M/yr wage · ${sg.years}-yr deal</div>
      <div class="fwd-rows">${fwdRow('Before',sg.before)}${fwdRow('After signing',sg.after)}</div>
      <div class="fwd-note">Adds <b>${eMv(sg.added_squad_cost)}/yr</b> squad cost (${eMv(sg.added_amortization)} amortization + ${eMv(sg.wage_eur_m)} wage + ${eMv(sg.added_agent)} agent).</div>
    </div>
    <div class="fwd-card">
      <div class="fwd-h">Contract renewal — ${rn.player}</div>
      <div class="fwd-sub">£${rn.wk_before_gbp_k}k/wk → £${rn.wk_after_gbp_k}k/wk (≈ +${eMv(rn.added_wage_eur_m)}/yr)</div>
      <div class="fwd-rows">${fwdRow('This season',rn.before)}${fwdRow('Next season',rn.after)}</div>
      <div class="fwd-note">Renewal trims next-season wage-bill headroom by <b>${eMv(rn.added_squad_cost)}</b>.</div>
    </div>
  </div>`;
}
async function loadFfpBrief(){
  const box=$('#ffpVerdict');
  box.innerHTML=`<div class="ffp-verdict loading"><span class="spin"></span> Generating board-level compliance verdict…</div>`;
  let r; try{ r=await api('/api/ffp/brief'); }catch(e){ box.innerHTML=''; return; }
  const b=r.brief;
  if(b){
    box.innerHTML=`<div class="ffp-verdict ${verdictCls(b.verdict)}">
      <div class="ffp-vbadge">${b.verdict}</div>
      <div class="ffp-vbody"><div class="ffp-vhead">${b.headline||''}</div>
        <div class="ffp-vso">${b.so_what||''}</div>
        ${b.recommendation?`<div class="ffp-vrec"><b>Recommendation:</b> ${b.recommendation}</div>`:''}</div>
      <span class="tf-src live" style="align-self:flex-start">${r.source}</span></div>`;
    typewrite(box.querySelector('.ffp-vhead'));
  } else { box.innerHTML=''; }
  // evidence cards
  const ev=$('#ffpEvidence');
  ev.innerHTML=(r.evidence||[]).map(e=>`<div class="ffp-ev-card">
    <div class="ffp-ev-h"><div><div class="ffp-ev-name">${e.player_name}</div><div class="ffp-ev-uri">${(e.file_uri||'').split('/').pop()}</div></div></div>
    <div class="ffp-ev-sum">${(e.ai_summary||'').slice(0,260)}</div></div>`).join('')
    ||'<div class="muted" style="font-size:12.5px">No contract evidence available.</div>';
}

/* ---------------- boot ---------------- */
wireTabs('#scoutTabs');wireTabs('#squadTabs');
$$('#agentTabs .tab').forEach(t=>t.onclick=()=>{location.hash='agents/'+t.dataset.sub;});
(async()=>{
  try{
    SQUAD=await api('/api/squad');
    $('#audioPlayer').innerHTML=SQUAD.map(p=>`<option value="${p.player_id}|${p.name}">${p.name} — ${p.club}</option>`).join('');
    INJURY=await api('/api/injury').catch(()=>[]); INJ_BY=Object.fromEntries(INJURY.map(r=>[r.player_id,r]));
    await loadHome(); await loadScouting(); loadSquad2(); await initScenarios();
    route();
  }catch(e){console.error(e);$('.wrap').insertAdjacentHTML('afterbegin',`<div class="status err" style="display:block;margin-bottom:16px">Load failed: ${e.message}</div>`);}
})();

/* ---------------- uploads (contract + audio) ---------------- */
function wireDrop(dropEl,inputEl,onFile){inputEl&&inputEl.addEventListener('change',()=>{if(inputEl.files[0])onFile(inputEl.files[0]);});}
$('#contractBtn')&&($('#contractBtn').onclick=()=>$('#contractFile').click());
const sevRank={high:0,medium:1,low:2};
function renderContractAnalysis(res){
  const box=$('#contractResult'); if(!box)return;
  if(!res||!res.ok||!res.analysis){
    box.innerHTML=`<div class="cr-card"><div class="cr-h"><b>Couldn't structure this document</b></div><div class="muted" style="font-size:12.5px">The file was parsed but the model didn't return clean fields. Raw text was still extracted on Databricks.</div></div>`;return;}
  const a=res.analysis;
  const term=(l,v)=>v?`<div class="cr-term"><span class="cr-tl">${l}</span><span class="cr-tv">${v}</span></div>`:'';
  const flags=(a.flags||[]).slice().sort((x,y)=>(sevRank[x.severity]??3)-(sevRank[y.severity]??3));
  box.innerHTML=`<div class="cr-card">
    <div class="cr-h"><div><div class="cr-title">${a.player||'Contract'}${a.club?` · <span class="muted">${a.club}</span>`:''}</div>
      <div class="cr-sub">Parsed &amp; analyzed live on Databricks</div></div>
      <span class="pill green">${flags.length} flag${flags.length===1?'':'s'} surfaced</span></div>
    <div class="cr-terms">${term('Contract end',a.end_date)}${term('Annual wage',a.annual_wage)}${term('Release clause',a.release_clause)}</div>
    ${a.summary?`<div class="cr-summary">${a.summary}</div>`:''}
    <div class="cr-flags">${flags.map(fl=>`<div class="cr-flag ${fl.severity||'low'}">
      <span class="cr-sev">${(fl.severity||'low').toUpperCase()}</span>
      <div><div class="cr-ft">${(fl.type||'').replace(/_/g,' ')}</div><div class="cr-fd">${fl.detail||''}</div></div></div>`).join('')}</div>
    <div class="cr-prov"><span class="dbx-dot"></span>${res.source||'ai_parse_document + ai_query'}</div>
  </div>`;
}
wireDrop(null,$('#contractFile'),async f=>{const st=$('#contractStatus');const box=$('#contractResult');if(box)box.innerHTML='';
  st.className='status work';st.textContent=`Uploading ${f.name}…`;
  try{const fd=new FormData();fd.append('file',f);const r=await api('/api/upload/contract',{method:'POST',body:fd});
    st.className='status work';st.innerHTML='Uploaded. <b>Parsing &amp; flagging</b> with <code>ai_parse_document</code> + <code>ai_query</code>…';
    if(box)box.innerHTML='<div class="cliploading"><span class="spin"></span> Reading the contract and checking clauses, cap space &amp; compliance…</div>';
    const a=await api('/api/contract/analyze?name='+encodeURIComponent(r.filename||f.name));
    st.className='status ok';st.textContent='Contract parsed — terms extracted and clauses flagged below.';
    renderContractAnalysis(a);}
  catch(e){st.className='status err';st.textContent=e.message;if(box)box.innerHTML='';}});
let mediaRec=null,chunks=[],recog=null,liveText='',recording=false;const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
$('#audioUploadBtn')&&($('#audioUploadBtn').onclick=()=>$('#audioFile').click());
$('#audioFile')&&$('#audioFile').addEventListener('change',()=>{if($('#audioFile').files[0])sendAudio($('#audioFile').files[0],liveText||null);});
$('#recBtn')&&($('#recBtn').onclick=async()=>{if(recording){stopRec();return;}
  try{const stream=await navigator.mediaDevices.getUserMedia({audio:true});chunks=[];liveText='';$('#liveTranscript').textContent='Listening…';
    mediaRec=new MediaRecorder(stream);mediaRec.ondataavailable=e=>chunks.push(e.data);
    mediaRec.onstop=()=>{const blob=new Blob(chunks,{type:'audio/webm'});sendAudio(new File([blob],'scout_note.webm',{type:'audio/webm'}),liveText);stream.getTracks().forEach(t=>t.stop());};
    mediaRec.start();
    if(SR){recog=new SR();recog.continuous=true;recog.interimResults=true;recog.lang='en-GB';recog.onresult=e=>{let t='';for(const r of e.results)t+=r[0].transcript;liveText=t;$('#liveTranscript').textContent=t;};recog.start();}
    else{$('#liveTranscript').textContent='(Live transcription not supported here — audio still captured.)';}
    recording=true;$('#recBtn').textContent='■ Stop & save';$('#recBtn').classList.add('on');
  }catch(e){const st=$('#audioStatus');st.className='status err';st.textContent='Mic error: '+e.message;}});
function stopRec(){recording=false;$('#recBtn').textContent='● Record note';$('#recBtn').classList.remove('on');try{recog&&recog.stop();}catch(e){}try{mediaRec&&mediaRec.stop();}catch(e){}}
async function sendAudio(file,transcript){const st=$('#audioStatus');const[pid,pname]=($('#audioPlayer').value||'p_unknown|Unknown').split('|');
  if(!transcript){st.className='status err';st.innerHTML='No transcript captured. Use <b>Record note</b> (live speech-to-text).';return;}
  st.className='status work';st.textContent='Saving note…';
  try{const fd=new FormData();fd.append('file',file);fd.append('player_id',pid);fd.append('player_name',pname);fd.append('scout_name',$('#audioScout').value||'App Upload');fd.append('transcript',transcript);
    const r=await api('/api/upload/audio',{method:'POST',body:fd});st.className='status ok';st.textContent='Scout note saved to the documents volume.';}
  catch(e){st.className='status err';st.textContent=e.message;}}

/* ---- page-aware "How this works" explainer (all Acme Agents pages + Clip Search) ---- */
const EXPLAINERS={
  transfer:{
    what:"Values any player from position-specific KPIs and recomputes live as you move the sliders — every euro explained factor by factor.",
    value:"A valuation you can defend in a negotiation: position-aware, transparent, and instantly re-runnable for what-if profiles — not a black-box number.",
    components:["Model Serving","MLflow pyfunc","Unity Catalog","Databricks Apps"],
    prompt:"Register a position-specific player-valuation model to Unity Catalog, serve it on Model Serving, and build a Databricks App where a sporting director drags KPI sliders and sees the value recompute live with per-factor contributions. Ground it in an Opta/StatsBomb KPI table; production path = AutoML on historical transfer fees."},
  physio:{
    what:"Fuses WHOOP recovery and STATSports GPS into one load picture, flags who's spiking on ACWR, and recommends next-fixture minutes — with the physio's own note folded in.",
    value:"Protects your most valuable assets: catch overload before it becomes a soft-tissue injury, and give the coach a defensible minutes call for the weekend.",
    components:["ai_query (FM)","Unity Catalog","Delta tables","Databricks Apps"],
    prompt:"On Databricks, fuse WHOOP recovery and STATSports GPS feeds into a Delta load_status table, compute ACWR and a next-fixture minutes recommendation, and use ai_query to generate a grounded rationale that also incorporates a free-text physio note. Surface it in a Databricks App."},
  nutrition:{
    what:"Gives each player a baseline fuelling plan, then uses AI to output the adjustments to make — grounded in their load, sleep and recovery, plus a spoken dietary note.",
    value:"Personalised sports nutrition at squad scale: the nutritionist reviews changes vs a baseline rather than a plan from scratch, and the player just talks.",
    components:["ai_query (FM)","Unity Catalog","Web Speech capture","Databricks Apps"],
    prompt:"On Databricks, derive a baseline nutrition plan per player from their load/recovery metrics, then use ai_query to return structured JSON adjustments (what to change and why) grounded in those metrics and a voice note transcribed in the app. Render baseline + deltas in a Databricks App."},
  coach:{
    what:"Reads the next opponent's event and tracking data and auto-writes a match-prep brief — how they hurt us, how we beat them, the key battle — with real scouting clips cited.",
    value:"A whole analyst's afternoon in one click, and every danger-man claim links to the actual film — data and video in one governed answer.",
    components:["ai_query (FM)","FM vision + embeddings","UC Volumes","Databricks Apps"],
    prompt:"On Databricks, model opponent event/tracking metrics in Delta, use ai_query to generate a structured match-prep brief, and cite scouting clips by reusing a vision-caption + embedding clip index stored in Unity Catalog Volumes. Serve it in a Databricks App."},
  financial:{
    what:"Models wage bill, transfer amortization, UEFA squad-cost ratio and PSR headroom from your real contracts, writes a board-level verdict, and runs forward-looking what-ifs.",
    value:"Tells the board how much you can actually spend this window — every figure derived and traceable to the signed contract PDF, not a black box.",
    components:["ai_query (FM)","FILE column + ai_parse_document","Unity Catalog","Databricks Apps"],
    prompt:"On Databricks, compute UEFA squad-cost ratio and PSR headroom from contract Delta tables, pull the governed contract PDFs via the FILE column + ai_parse_document as evidence, use ai_query for a board-level verdict, and model forward-looking scenarios (Champions League revenue, a new signing, a renewal) in a Databricks App."},
  ask:{
    what:"One place to ask questions across your whole estate in plain language — the Acme Scout Genie agent answers in Agent mode, blending your squad tables with the contract PDFs and scout transcripts, and cites every source.",
    value:"Every club gets a single, governed front door to their data — directors and analysts self-serve answers over structured data AND unstructured documents, in their own tenant, without a BI ticket.",
    components:["Genie / Acme One","Agent mode (blended)","Unity Catalog","UC Volumes"],
    prompt:"On Databricks, create a Genie space over the governed squad tables and attach the contract-PDF + scout-transcript volume, enable Agent mode so it blends structured and unstructured sources into one cited answer, and expose it in a Databricks App. Point Claude Code at the genie-code MCP to improve the generated SQL."},
  clips:{
    what:"Searches your scouting film by name or by what's happening on the pitch — a name resolves deterministically to that one player; a description falls back to semantic similarity.",
    value:"Turns a video archive nobody opened into an instantly searchable asset — by player or by scene — on the same governed platform.",
    components:["FM vision captioning","Embeddings","Vector similarity","UC Volumes"],
    prompt:"On Databricks, frame-sample scouting videos, caption each with a vision FM, embed the captions with an embedding model, and store them in a clip_index over Unity Catalog Volumes. Build a Databricks App that resolves a name query to one player and a descriptive query via vector similarity."},
};
let explainerAutoShown=false;
function setExplainer(key){
  const wrap=$('#explainer'); if(!wrap)return;
  const pop=$('#explainerPop'); if(pop)pop.hidden=true;
  const e=EXPLAINERS[key];
  if(!e){wrap.hidden=true;return;}
  wrap.hidden=false;
  $('#epBody').innerHTML=`
    <div class="ep-sec"><div class="ep-l">What it does</div><p>${e.what}</p></div>
    <div class="ep-sec"><div class="ep-l">Value it unlocks</div><p>${e.value}</p></div>
    <div class="ep-sec"><div class="ep-l">Databricks components powering it</div><div class="ep-chips">${e.components.map(c=>`<span>${c}</span>`).join('')}</div></div>
    <div class="ep-sec"><div class="ep-l">Build this with Genie</div><div class="ep-prompt"><code id="epPrompt">${e.prompt}</code><button class="ep-copy" id="epCopy">Copy prompt</button></div></div>`;
  const copy=$('#epCopy'); if(copy)copy.onclick=async()=>{try{await navigator.clipboard.writeText($('#epPrompt').textContent.trim());
    copy.textContent='Copied';setTimeout(()=>copy.textContent='Copy prompt',1500);}catch(e){copy.textContent='Copy failed';}};
  // auto-surface the explainer the first time an agent/clip page is opened this session
  if(pop && !explainerAutoShown){explainerAutoShown=true;setTimeout(()=>{pop.hidden=false;},350);}
}
(function(){
  const wrap=$('#explainer'), btn=$('#explainerBtn'), pop=$('#explainerPop'), x=$('#explainerX');
  if(!wrap||!btn||!pop)return;
  const toggle=show=>{pop.hidden=(show===undefined)?!pop.hidden:!show;};
  btn.onclick=e=>{e.stopPropagation();toggle();};
  if(x)x.onclick=()=>toggle(false);
  document.addEventListener('click',e=>{if(!pop.hidden && !wrap.contains(e.target))toggle(false);});
})();
