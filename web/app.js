'use strict';
const $ = s => document.querySelector(s);
let projectData = {}, bearer = '';
let identityEpoch = 0, identityController = new AbortController();
const pendingButtons = new Map();
function identityScope(){return {epoch:identityEpoch, signal:identityController.signal};}
function requireIdentity(scope){if(!scope || scope.epoch!==identityEpoch || scope.signal.aborted)throw new DOMException('Identity changed', 'AbortError');}
function clearIdentityViews(){
  identityEpoch++;
  identityController.abort();
  identityController=new AbortController();
  for(const id of ['answer-result','comparison','change-output','saved-answers','review-output','security-result','documents','evaluation-output'])document.getElementById(id).replaceChildren();
  for(const button of pendingButtons.keys()){button.disabled=false;button.removeAttribute('aria-busy');}
  pendingButtons.clear();
  projectData={};
  for(const id of ['project','release','compare-project','left','right'])document.getElementById(id).replaceChildren();
  $('#health').textContent='Connecting…';
  $('#error').hidden=true;
  $('#error').textContent='';
}
// Reset synchronously before a new handler captures its request scope.
function identityChange(fn){const run=guard(fn);return event=>{clearIdentityViews();return run(event);};}
const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safeURL = value => {try {const u=new URL(value);return u.protocol==='https:' ? u.href : '#';} catch {return '#';}};
async function api(path, body, scope) {
  requireIdentity(scope);
  try {
    const response = await fetch(path, {signal:scope.signal, method: body === undefined ? 'GET' : 'POST', headers:{'Content-Type':'application/json','X-Demo-Role':$('#role').value,...(bearer?{'Authorization':`Bearer ${bearer}`}:{})}, ...(body===undefined?{}:{body:JSON.stringify(body)})});
    const data = await response.json();
    // Aborting transport is not enough: parsing may already have completed.
    requireIdentity(scope);
    if (!response.ok) throw new Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail));
    return data;
  } catch(error) {
    requireIdentity(scope);
    throw error;
  }
}
function guard(fn) {return async event => {
  if(event)event.preventDefault();
  const scope=identityScope(), job={};
  $('#error').hidden=true;
  const button=event?.submitter||event?.target?.closest('button')||event?.currentTarget;
  if(button?.tagName==='BUTTON'){pendingButtons.set(button,job);button.disabled=true;button.setAttribute('aria-busy','true');}
  try{await fn(event,scope);}catch(error){
    if(scope.epoch===identityEpoch && error.name!=='AbortError'){$('#error').textContent=error.message;$('#error').hidden=false;}
  }finally{
    if(pendingButtons.get(button)===job){pendingButtons.delete(button);button.disabled=false;button.removeAttribute('aria-busy');}
  }
};}
function sourceCard(p) {return `<article class="source-card"><span class="pill">${escape(p.source_type==='synthetic'?'SYNTHETIC FIXTURE':'UPSTREAM SNAPSHOT')} · ${escape(p.release)}</span><h4>${escape(p.section)}</h4><p>${escape(p.quote)}</p>${p.source_type==='upstream'?`<a href="${escape(safeURL(p.source_url))}" target="_blank" rel="noopener noreferrer">Immutable source ↗</a>`:'<span class="meta">Original teaching example · not an upstream quotation</span>'}<code>Passage ${escape(p.passage_id)}<br>Revision ${escape(p.revision_id)}<br>SHA256 ${escape(p.normalized_hash)}</code></article>`;}
function renderAnswer(a) {return `<article class="panel result"><div class="result-header"><h2>${escape(a.project)} <span class="status">${escape(a.release)}</span></h2><span class="pill">${a.claims.length} CITED EXTRACTS</span></div>${a.abstention_reason?`<p class="abstention">${escape(a.abstention_reason)}</p>`:`<div class="answer-text">${escape(a.answer)}</div>`}<div class="meta"><span>${escape(a.metadata.mode)}</span><span>${escape(a.metadata.latency_ms)} ms</span><span>${escape(a.metadata.embedding)}</span><span>${escape(a.metadata.generation)}</span></div><details><summary class="meta">Evidence inspector · ${a.passages.length} passages</summary><div class="source-list">${a.passages.map(sourceCard).join('')}</div></details></article>`;}
function options(values){return values.map(v=>`<option>${escape(v)}</option>`).join('');}
function releases(){const values=projectData[$('#project').value]||[];$('#release').innerHTML=options(values);}
function compareReleases(){const values=projectData[$('#compare-project').value]||[];$('#left').innerHTML=options(values);$('#right').innerHTML=options(values);if(values.length>1)$('#right').selectedIndex=values.length-1;}
async function load(scope){const health=await api('/health',undefined,scope);if(!health.generator.startsWith('deterministic'))document.querySelector('.notice').textContent='Compatible provider mode: exact extract selection. Inspect response metadata for invocation and usage.';$('#health').textContent=`${health.database} · connected`;$('#role').disabled=!health.demo;projectData=await api('/api/projects',undefined,scope);const names=Object.keys(projectData).sort((a,b)=>a==='pydantic'?-1:b==='pydantic'?1:a.localeCompare(b));$('#project').innerHTML=options(names);$('#compare-project').innerHTML=options(names);releases();compareReleases();}
async function showView(view,scope){requireIdentity(scope);for(const el of document.querySelectorAll('.view'))el.hidden=el.id!==`view-${view}`;for(const b of document.querySelectorAll('nav button'))b.classList.toggle('active',b.dataset.view===view);$('#crumb').textContent=document.querySelector(`[data-view="${view}"] span`).textContent;if(view==='changes')await savedAnswers(scope);if(view==='security')await documents(scope);if(view==='evaluation')await evaluation(scope);}
async function savedAnswers(scope){const data=await api('/api/answers',undefined,scope);$('#saved-answers').innerHTML=data.length?data.map(a=>`<div class="saved-row"><div><p>${escape(a.question)}</p><small>${escape(a.project)} / ${escape(a.release)} · ${escape(a.id.slice(0,8))}</small></div><span class="status ${a.status.includes('pending')?'pending':a.status==='confirmed_stale'?'stale':''}">${escape(a.status.replaceAll('_',' '))}</span><div><button data-review="${escape(a.id)}">Revalidate</button> <button data-history="${escape(a.id)}">History</button></div></div>`).join(''):'<div class="empty">No saved answers for this identity.</div>';}
async function updateDemo(formatOnly,scope){if($('#role').value!=='admin'&&!bearer)throw new Error('Select Administrator for this synthetic update.');const docs=await api('/api/documents',undefined,scope);const doc=docs.find(d=>d.project==='demo'&&d.key==='timeout-policy');if(!doc)throw new Error('Synthetic timeout document is not present. Start with --demo.');const detail=await api('/api/documents/'+doc.id,undefined,scope);const text=detail.passages[0].quote;const current=(text.match(/to (\d+) seconds/)||[])[1];if(!current)throw new Error('The teaching fixture was edited outside this scenario.');const value=formatOnly?current:(current==='30'?'60':'30');const nextText=formatOnly?text+'  \n':`Synthetic service timeout policy: set request_timeout to ${value} seconds.`;const result=await api('/api/ingest',{project:'demo',release:'1.0',document_key:'timeout-policy',classification:'public',source_type:'synthetic',source_url:'https://example.invalid/synthetic/timeout-policy',license:'MIT (original ReleaseLens synthetic fixture)',attribution:'ReleaseLens AI-assisted synthetic teaching dataset',expected_revision:doc.revision_id,sections:[{key:'timeout-policy',title:'timeout policy',text:nextText,fact_key:'request_timeout',fact_value:value}]},scope);$('#change-output').innerHTML=`<div class="panel result"><h3>${escape(result.kind.replaceAll('_',' '))}</h3><p>${result.affected_answer_ids.length} of your saved answers queued for review.</p><details><summary>Document diff</summary><pre>${escape(JSON.stringify(await api('/api/documents/'+doc.id+'/changes',undefined,scope),null,2))}</pre></details></div>`;await savedAnswers(scope);}
async function documents(scope){const docs=await api('/api/documents',undefined,scope);$('#documents').innerHTML=`<div class="panel"><table><thead><tr><th>PROJECT</th><th>RELEASE</th><th>DOCUMENT</th><th>CLASSIFICATION</th></tr></thead><tbody>${docs.map(d=>`<tr><td>${escape(d.project)}</td><td>${escape(d.release)}</td><td>${escape(d.key)}</td><td>${escape(d.classification)}</td></tr>`).join('')}</tbody></table></div>`;}
async function evaluation(scope){const data=await api('/api/evaluation',undefined,scope);if(data.status==='not_run'){$('#evaluation-output').innerHTML='<div class="panel">Benchmark not run. Execute python -m releaselens.evaluate.</div>';return;}const rows=data.baselines||[];$('#evaluation-output').innerHTML=`<div class="notice"><span class="pill">${escape(data.dataset_review_status)}</span>${escape(data.scope)}</div><div class="panel"><table><thead><tr><th>CONFIGURATION</th><th>RECALL@4</th><th>MRR</th><th>WRONG RELEASE</th><th>P95 / MS</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${escape(r.mode)}</td><td>${(r.recall_at_4*100).toFixed(1)}%</td><td>${r.mrr.toFixed(3)}</td><td>${r.wrong_release_queries}/${r.queries}</td><td>${r.p95_ms.toFixed(2)}</td></tr>`).join('')}</tbody></table><p class="meta">${escape(data.limitations)}</p><details><summary>Full reproducible artifact</summary><pre>${escape(JSON.stringify(data,null,2))}</pre></details></div>`;}
document.querySelectorAll('nav button').forEach(b=>b.addEventListener('click',guard((_,scope)=>showView(b.dataset.view,scope))));
$('#project').addEventListener('change',releases);$('#compare-project').addEventListener('change',compareReleases);
$('#role').addEventListener('change',identityChange(async(_,scope)=>{await load(scope);const view=document.querySelector('nav button.active').dataset.view;await showView(view,scope);}));
document.querySelectorAll('[data-question]').forEach(b=>b.addEventListener('click',()=>{$('#question').value=b.dataset.question;}));
$('#ask-form').addEventListener('submit',guard(async(_,scope)=>{const result=await api('/api/ask',{project:$('#project').value,release:$('#release').value,question:$('#question').value,mode:$('#mode').value,k:2,save:true},scope);$('#answer-result').innerHTML=renderAnswer(result);}));
$('#compare-form').addEventListener('submit',guard(async(_,scope)=>{const result=await api('/api/compare',{project:$('#compare-project').value,left:$('#left').value,right:$('#right').value,question:$('#compare-question').value},scope);$('#comparison').innerHTML=renderAnswer(result.left)+renderAnswer(result.right);}));
$('#demo-save').addEventListener('click',guard(async(_,scope)=>{const result=await api('/api/ask',{project:'demo',release:'1.0',question:'What is the request_timeout policy?',k:1},scope);$('#change-output').innerHTML=renderAnswer(result);await savedAnswers(scope);}));
$('#demo-technical').addEventListener('click',guard((_,scope)=>updateDemo(false,scope)));$('#demo-format').addEventListener('click',guard((_,scope)=>updateDemo(true,scope)));$('#refresh-answers').addEventListener('click',guard((_,scope)=>savedAnswers(scope)));
$('#saved-answers').addEventListener('click',guard(async(e,scope)=>{const b=e.target.closest('button');if(!b)return;const id=b.dataset.review||b.dataset.history;if(b.dataset.review){const result=await api(`/api/answers/${id}/revalidate`,{},scope);const correction=result.assessment.corrected_answer_id;$('#review-output').innerHTML=`<div class="panel result"><h2>${escape(result.status.replaceAll('_',' '))}</h2><p>Original answer and evidence preserved.</p><pre>${escape(JSON.stringify(result.assessment,null,2))}</pre></div>`+(correction?renderAnswer((await api('/api/answers/'+correction,undefined,scope)).payload):'');await savedAnswers(scope);}else{$('#review-output').innerHTML=`<pre>${escape(JSON.stringify(await api(`/api/answers/${id}/history`,undefined,scope),null,2))}</pre>`;}}));
$('#security-probe').addEventListener('click',guard(async(_,scope)=>{$('#security-result').innerHTML=renderAnswer(await api('/api/ask',{project:'demo',release:'1.0',question:'CANARY-ORCHID-7814',k:1},scope));}));
$('#auth-toggle').addEventListener('click',()=>{$('#auth-panel').hidden=!$('#auth-panel').hidden;});$('#auth-apply').addEventListener('click',identityChange(async(_,scope)=>{bearer=$('#token').value.trim();$('#token').value='';await load(scope);$('#auth-panel').hidden=true;const view=document.querySelector('nav button.active').dataset.view;await showView(view,scope);}));
guard((_,scope)=>load(scope))();
