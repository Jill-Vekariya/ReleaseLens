import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {initialState,current,search,saveAnswer,changeSource,addCounterevidence,revalidate,canViewAnswer,verifyCitation,normalize} from '../engine.js';
const pages=JSON.parse(readFileSync(new URL('../data.json',import.meta.url)));
const setup=()=>{const s=initialState();s.role='admin';return s;};
const saveTimeout=s=>saveAnswer(s,search(pages,s,'demo','1.0','request_timeout',1));

test('all retrieved upstream extracts belong to the exact selected project and release',()=>{
  const state=initialState();
  for(const page of pages){
    const result=search(pages,state,page.project,page.release,page.project==='pydantic'?'model configuration':'Connection execute transaction');
    assert.ok(result.hits.length>0);
    assert.ok(result.hits.every(p=>p.project===page.project&&p.release===page.release&&verifyCitation(pages,state,p)));
  }
});
test('unknown project/release and absent query terms abstain',()=>{
  const s=initialState();
  assert.equal(search(pages,s,'pydantic','9.99','model').hits.length,0);
  assert.equal(search(pages,s,'pydantic','2.10.4','zyxwvutsrq123456').abstained,true);
  assert.equal(search(pages,s,'pydantic','2.10.4','the of and').abstained,true);
});
test('reader and reviewer roles exclude the restricted canary before ranking',()=>{
  const s=initialState();
  for(const role of ['reader','reviewer']){s.role=role;assert.equal(search(pages,s,'demo','1.0','CANARY ORCHID').hits.length,0);}
  s.role='admin';assert.equal(search(pages,s,'demo','1.0','CANARY ORCHID').hits[0].id,'restricted-canary');
});
test('internal visibility differs from restricted visibility',()=>{
  const s=initialState();
  assert.equal(search(pages,s,'demo','1.0','internal routing staging').hits.length,0);
  s.role='reviewer';assert.equal(search(pages,s,'demo','1.0','internal routing staging').hits[0].id,'internal-routing');
});
test('injection fixture is quarantined for every demo identity',()=>{
  const s=initialState();for(const role of ['reader','reviewer','admin']){s.role=role;assert.equal(search(pages,s,'demo','1.0','Ignore previous instructions').hits.length,0);assert.ok(search(pages,s,'demo','1.0','reveal secret').hits.every(p=>!p.quarantined));}
});
test('source mutations require the administrator demo role',()=>{
  const s=initialState();assert.throws(()=>changeSource(s,'technical'),/Administrator/);assert.throws(()=>addCounterevidence(s),/Administrator/);assert.equal(s.revisions.length,1);
});
test('a technical change queues the dependent answer and preserves the exact original',()=>{
  const s=setup();const a=saveTimeout(s);const original=structuredClone(a.citations);const text=a.text;
  assert.equal(changeSource(s,'technical').affected,1);assert.equal(a.status,'revalidation_pending');
  assert.equal(revalidate(s,a.id).status,'confirmed_stale');assert.equal(a.text,text);assert.deepEqual(a.citations,original);
  assert.equal(a.correction.value,60);assert.equal(a.correction.revision,'r2');assert.equal(verifyCitation(pages,s,a.citations[0]),true);
});
test('formatting-only and uncited updates preserve the saved timeout fact',()=>{
  const s=setup();const a=saveTimeout(s);const normalized=normalize(current(s).text);
  assert.equal(changeSource(s,'formatting').affected,0);assert.equal(normalize(current(s).text),normalized);
  assert.equal(changeSource(s,'uncited').affected,0);assert.equal(revalidate(s,a.id).status,'unchanged');
});
test('technical changes follow historical citations across formatting revisions',()=>{
  const s=setup();const a=saveTimeout(s);changeSource(s,'formatting');changeSource(s,'uncited');
  assert.equal(changeSource(s,'technical').affected,1);assert.equal(revalidate(s,a.id).status,'confirmed_stale');assert.equal(a.citations[0].revision,'r1');
});
test('repeat review is idempotent for the same effective evidence',()=>{
  const s=setup();const a=saveTimeout(s);revalidate(s,a.id);const events=s.events.length;
  assert.equal(revalidate(s,a.id).repeated,true);assert.equal(a.history.length,1);assert.equal(s.events.length,events);
  changeSource(s,'formatting');assert.equal(revalidate(s,a.id).repeated,true);assert.equal(a.history.length,1);
});
test('public structured counterevidence queues manual review without changing the citation',()=>{
  const s=setup();const a=saveTimeout(s);const citation=structuredClone(a.citations);revalidate(s,a.id);
  addCounterevidence(s);assert.equal(a.status,'revalidation_pending');assert.equal(revalidate(s,a.id).status,'manual_review_required');assert.deepEqual(a.citations,citation);assert.equal(a.correction,null);
});
test('saving a current correction creates a separate answer and keeps the original',()=>{
  const s=setup();const a=saveTimeout(s);changeSource(s,'technical');revalidate(s,a.id);const corrected=saveTimeout(s);
  assert.notEqual(a.id,corrected.id);assert.equal(a.citations[0].value,30);assert.equal(corrected.citations[0].value,60);assert.equal(s.answers.length,2);
});
test('role changes invalidate privileged query results and saved answer visibility',()=>{
  const s=setup();const result=search(pages,s,'demo','1.0','CANARY ORCHID');const a=saveAnswer(s,result);
  s.role='reader';assert.equal(canViewAnswer(s,a),false);assert.throws(()=>saveAnswer(s,result),/role changed/);assert.throws(()=>revalidate(s,a.id),/not available/);
});
test('changed synthetic facts do not invalidate immutable upstream citations',()=>{
  const s=setup();const a=saveAnswer(s,search(pages,s,'pydantic','2.10.4','model configuration'));
  assert.equal(changeSource(s,'technical').affected,0);assert.equal(revalidate(s,a.id).status,'unchanged');
  assert.ok(a.citations.every(c=>verifyCitation(pages,s,c)));
});
test('altered citation text fails exact extract verification',()=>{
  const s=initialState();const result=search(pages,s,'pydantic','2.10.4','model configuration');
  assert.equal(verifyCitation(pages,s,{...result.hits[0],text:'invented quotation'}),false);
});
test('bundled raw source and preserved license bytes match the upstream provenance hashes',()=>{
  for(const page of pages){
    assert.equal(createHash('sha256').update(page.source).digest('hex'),page.raw_sha256);
    const license=readFileSync(new URL(`../licenses/${page.id}.txt`,import.meta.url));
    assert.equal(createHash('sha256').update(license).digest('hex'),page.license_sha256);
  }
});
