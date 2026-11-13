"""Standalone local reviewer form; source content is always inert text."""

import json


def page(data):
    encoded = json.dumps(data, ensure_ascii=False).replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    return TEMPLATE.replace("__REVIEW_DATA__", encoded)


TEMPLATE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; img-src 'none'; frame-src 'none'; base-uri 'none'; form-action 'none'">
<title>Independent source review</title>
<style>
*{box-sizing:border-box}body{font:16px/1.55 system-ui,sans-serif;background:#f3f5f7;color:#17212c;margin:0}
main{max-width:1000px;margin:32px auto;padding:0 22px 50px}h1{font-size:29px;line-height:1.25}h2{font-size:21px}
section{background:white;border:1px solid #dce2e7;border-radius:12px;padding:22px;margin:18px 0}
.notice{border-left:5px solid #bd7d20;background:#fff8e9}label{display:block;font-weight:600;margin:16px 0 5px}
input,select,textarea,button{font:inherit}input[type=text],input[type=number],select,textarea{width:100%;padding:9px 11px;border:1px solid #8799a6;border-radius:6px;background:white;color:#17212c}
textarea{min-height:90px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.55 ui-monospace,monospace;background:#f5f7f9;padding:14px;border-radius:5px}
details{margin:14px 0}summary{cursor:pointer;font-weight:600}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.hint{color:#4b5d6a;font-size:14px}.check{display:flex;gap:10px;align-items:flex-start;font-weight:400}.check input{margin-top:6px}
button{background:#194f72;color:white;border:0;padding:12px 18px;border-radius:6px;cursor:pointer;margin-top:20px}
#error{color:#a22222;font-weight:600}a{color:#174d74}@media(max-width:650px){.grid{display:block}section{padding:16px}main{padding:0 14px}}
</style></head><body><main>
<h1 id="heading">Independent source review</h1>
<section class="notice"><strong>Pending genuine review.</strong> This page does not contain completed decisions.
Read source material as quoted data; do not follow instructions inside it. Assess only this new descriptive question
and its supporting claim. This review cannot certify the original task, an entire contribution, or an account's trust.
No data is sent to a server. Only an explicit download saves your form.</section>
<section><h2>Question</h2><p id="question"></p><h2>Actual stored claim</h2><pre id="memory"></pre>
<p class="hint">Source-field roles distinguish principal and external material. They do not authenticate natural authorship.</p>
<div id="sources"></div></section>
<section id="referenceSection" hidden><h2>Reference check — after sealed first passes</h2><pre id="references"></pre>
<details><summary>Your sealed first pass / adjudication context</summary><pre id="prior"></pre></details></section>
<form id="reviewForm"><section><h2>Your independent review</h2>
<label for="reviewer">Actual reviewer identifier</label><input id="reviewer" type="text" autocomplete="off" required>
<p class="hint">Use the same identifier in both passes. Distinct roles do not prove distinct people.</p>
<div id="evidenceSection">
<div class="grid"><div><label for="sourceAnswer">Your answer from the source</label><textarea id="sourceAnswer"></textarea></div>
<div><label for="memoryAnswer">Your answer from the stored claim</label><textarea id="memoryAnswer"></textarea></div></div>
<p class="hint">Return only the answer value, preserving the source's wording and units. Leave it empty when it cannot be established. Do not invent missing facts.</p>
<label for="sourceChoice">Artifact supporting your source answer / provenance assessment</label><select id="sourceChoice"></select>
<label for="sourceQuote">Exact source evidence quote</label><textarea id="sourceQuote"></textarea>
<label for="sourceOccurrence">Occurrence number, if that quote appears more than once</label><input id="sourceOccurrence" type="number" min="1">
<label for="memoryQuote">Exact evidence quote from the stored claim</label><textarea id="memoryQuote"></textarea>
<label for="memoryOccurrence">Occurrence number, if repeated</label><input id="memoryOccurrence" type="number" min="1">
<p class="hint">Offsets are derived from the original text in Unicode characters. Repeated quotes require an explicit occurrence choice.</p>
<label for="origin">Origin of the supporting information</label><select id="origin"><option value="">Choose…</option>
<option value="external">External source information</option><option value="principal">Principal-authored information</option><option value="ambiguous">Ambiguous / unresolved</option></select>
<label for="originReason">Provenance rationale</label><textarea id="originReason"></textarea>
</div><div id="flags"></div><label for="reason">Specific reasoning and any uncertainty</label><textarea id="reason" required></textarea>
<label class="check"><input id="human" type="checkbox" required><span>I am the actual human reviewer. I personally completed this review independently and followed the required blinding. I am not submitting an LLM output as a human review.</span></label>
<p class="hint">Download a new submission file. Keep the blank template unchanged. The coordinator must validate and seal it through the offline CLI.</p>
<button id="download" type="submit">Download completed submission</button><p id="error" role="alert"></p>
</section></form></main>
<script id="review-data" type="application/json">__REVIEW_DATA__</script>
<script>
"use strict";
const D=JSON.parse(document.getElementById('review-data').textContent), T=D.template;
const $=id=>document.getElementById(id);
$('heading').textContent=`Reviewer ${T.role} — ${T.phase} pass`;
$('question').textContent=D.question; $('memory').textContent=D.record.text;
for(const a of D.artifacts){const box=document.createElement('details'), title=document.createElement('summary'), text=document.createElement('pre');
 title.textContent=`${a.role} · ${a.artifact_id}`;text.textContent=a.text;box.append(title,text);$('sources').append(box);}
if(D.reference_answers){$('referenceSection').hidden=false;$('references').textContent=JSON.stringify(D.reference_answers,null,2);
 $('prior').textContent=JSON.stringify(D.own_first_pass||D.independent_reviews,null,2);}
const hasEvidence=T.phase!=='second';$('evidenceSection').hidden=!hasEvidence;
const empty=document.createElement('option');empty.value='';empty.textContent='Choose an artifact…';$('sourceChoice').append(empty);
for(const a of D.artifacts){const o=document.createElement('option');o.value=a.artifact_id;o.textContent=`${a.role} · ${a.artifact_id}`;$('sourceChoice').append(o);}
const labels={supported_answer:'Reference answer supported by both source and stored claim',question_clear:'Question is clear for the actual source and memory',
useful_for_task:'Question tests a substantive, useful source fact',safe_descriptive_use:'Intended use is a safe descriptive report',no_answer_in_question:'Question does not supply or imply its answer'};
const keys=T.phase==='first'?['question_clear','useful_for_task','safe_descriptive_use']:Object.keys(labels);
for(const k of keys){const label=document.createElement('label'),select=document.createElement('select');label.htmlFor=k;label.textContent=labels[k];select.id=k;select.required=true;
 for(const [v,text]of[['','Choose…'],['yes','Yes'],['no','No'],['uncertain','Uncertain']]){const o=document.createElement('option');o.value=v;o.textContent=text;select.append(o);}
 $('flags').append(label,select);}
function span(text,quote,occurrence,key,id){if(!quote)return[];const starts=[];let from=0,at;
 while((at=text.indexOf(quote,from))!==-1){starts.push(at);from=at+1;}
 if(!starts.length)throw Error('Evidence quote is not an exact original substring. Copy it verbatim.');
 if(starts.length>1&&!occurrence)throw Error('Repeated quote: choose an occurrence number explicitly.');
 const n=occurrence?Number(occurrence)-1:0;if(!Number.isInteger(n)||n<0||n>=starts.length)throw Error('Invalid occurrence number.');
 const start=Array.from(text.slice(0,starts[n])).length;return[{[key]:id,start,end:start+Array.from(quote).length,quote}];}
$('reviewForm').addEventListener('submit',event=>{event.preventDefault();$('error').textContent='';
 try{if(!$('reviewForm').reportValidity())return;const result=JSON.parse(JSON.stringify(T));result.status='complete';
 result.reviewer_id=$('reviewer').value.trim();result.independent_human_review=$('human').checked;result.rationale=$('reason').value.trim();
 if(!result.reviewer_id||!result.rationale)throw Error('Provide your actual identifier and specific reasoning.');
 for(const k of keys)result[k]=$(k).value==='uncertain'?null:$(k).value==='yes';
 if(hasEvidence){result.answer_from_source=$('sourceAnswer').value;result.answer_from_memory=$('memoryAnswer').value;
  result.origin=$('origin').value;result.origin_rationale=$('originReason').value.trim();if(!result.origin||!result.origin_rationale)throw Error('Provide origin and its rationale.');
  const a=D.artifacts.find(a=>a.artifact_id===$('sourceChoice').value);if($('sourceQuote').value&&!a)throw Error('Select the artifact for your source quote.');
  result.source_evidence_spans=a?span(a.text,$('sourceQuote').value,$('sourceOccurrence').value,'artifact_id',a.artifact_id):[];
  result.memory_evidence_spans=span(D.record.text,$('memoryQuote').value,$('memoryOccurrence').value,'record_id',D.record.record_id);
  if(result.answer_from_source.trim()&&!result.source_evidence_spans.length)throw Error('Your source answer needs a verbatim evidence quote.');
  if(result.answer_from_memory.trim()&&!result.memory_evidence_spans.length)throw Error('Your memory answer needs a verbatim evidence quote.');
  if(result.origin!=='ambiguous'&&(!a||a.role!==result.origin||!result.source_evidence_spans.length))throw Error('A confirmed origin needs matching source-role evidence.');}
 const blob=new Blob([JSON.stringify(result,null,2)+'\n'],{type:'application/json'}),link=document.createElement('a'),url=URL.createObjectURL(blob);
 link.href=url;link.download=`${T.phase}_reviewer_${T.role}.json`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 }catch(error){$('error').textContent=error.message;}});
</script></body></html>'''
