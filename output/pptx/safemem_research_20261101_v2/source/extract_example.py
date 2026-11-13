import json,gzip,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).parent
old=json.loads((ROOT/'output/pptx/safemem_research_20261101/source/verified_data.json').read_text())
e='ep_43547fc840a2c88dacd18bd7';r=ROOT/'research_data/provisional_extension_freeze_v1_20261101/private';p=json.loads((r/(e+'.json')).read_text());s=json.load(gzip.open(r/(e+'.json.gz'),'rt'))
idx={x['contribution_id']:x for x in map(json.loads,(ROOT/'research_data/mpbench_provisional_v1_20261029/private/evaluator_case_index.jsonl').open())}
origins={x['origin']['root_id']:x['origin'] for x in s['evidence']['events']}
trace=[]
for j,a in enumerate(p['audits']):
 pid=next(x['contribution_id'] for x in p['provenance_decisions'] if x['root_id']==a['root_id'])
 trace.append(dict(ticket='A'+str(j),origin=origins[a['root_id']],case=idx[pid],audit=a))
pid=trace[2]['case']['contribution_id']
packet=next(x for x in map(json.loads,(ROOT/'research_data/mpbench_provisional_v1_20261029/private/review_packets.jsonl').open()) if x['contribution_id']==pid)
case=None
for l in (ROOT/'data/mpbench/adversarial_data.jsonl.jsonl').open():
 try:x=json.loads(l)
 except json.JSONDecodeError:continue
 if x['id']=='ADV_2962':case=x;break
record=next(x for x in packet['records'] if x['record_id']=='e_63f1695485cf0b04591be8a9')
artifact=next(x for x in packet['artifacts'] if x['artifact_id']==record['construction_source_spans'][0]['artifact_id'])
for span in record['construction_source_spans']:assert artifact['text'][span['start']:span['end']]==span['quote']
bind=next(x for x in s['bindings']['records'] if x['record_id']==record['record_id'])
assert bind['content_hash']==record['content_hash']
case_batches={}
for x in p['provenance_decisions']:
 o=origins[x['root_id']]
 if o['attribution']=='authenticated_external' and o['contributor_id']==trace[2]['origin']['contributor_id'] and o['context_id']=='file_and_doc':
  case_batches.setdefault(o['batch_id'],{})[x['contribution_id']]=idx[x['contribution_id']]['original_id']
new=dict(case=case,packet=packet,record=record,artifact=artifact,binding=bind,trace=trace,batches={k:sorted(v.values()) for k,v in case_batches.items()},frozen_episode=e)
old['walkthrough']=new
old['source_sha256']['research_data/mpbench_provisional_v1_20261029/private/review_packets.jsonl']=hashlib.sha256((ROOT/'research_data/mpbench_provisional_v1_20261029/private/review_packets.jsonl').read_bytes()).hexdigest()
(OUT/'verified_data.json').write_text(json.dumps(old,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'case':case['id'],'span_checks':len(record['construction_source_spans']),'batches':new['batches'],'audit_cases':[x['case']['original_id'] for x in trace]},indent=2))
