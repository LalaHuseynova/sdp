import json,gzip,sqlite3
from pathlib import Path
from ams.data.mpbench import _read_objects
from ams.research.provisional.episodes import recode
R=Path(__file__).resolve().parents[4];O=Path(__file__).parent
b=R/'research_data/mpbench_provisional_v1_20261029';f=R/'research_data/provisional_extension_freeze_v1_20261101/private';eid='ep_43547fc840a2c88dacd18bd7'
p=json.loads((f/(eid+'.json')).read_text());s=json.load(gzip.open(f/(eid+'.json.gz'),'rt'))
key=bytes.fromhex(json.loads((R/'research_data/mpbench_phase1/private/identifier_key.json').read_text())['hex_key'])
ix={a['contribution_id']:a for a in map(json.loads,(b/'private/evaluator_case_index.jsonl').open())}
packets={a['contribution_id']:a for a in map(json.loads,(b/'private/review_packets.jsonl').open()) if a['contribution_id'] in {x['contribution_id'] for x in p['provenance_decisions']}}
oldpub=json.loads((b/'public/g_119618b1f6801d98f0a881f7'/(eid+'.json')).read_text())['overlay']
links={x['record_id']:x for x in s['bindings']['records']}; claims={x['claim_id']:x for _,g in s['graphs'] for x in g['claims']};chunks={x['chunk_id']:x for _,g in s['chunks'] for x in g}
rootmap={x['origin']['root_id']:x['origin'] for x in s['evidence']['events']}
raw={a['id']:a for a in _read_objects(R/'data/mpbench/adversarial_data.jsonl.jsonl')+_read_objects(R/'data/mpbench/benign_data.jsonl.jsonl')}
aud=[]
for j,a in enumerate(p['audits']):
 pid=next(x['contribution_id'] for x in p['provenance_decisions'] if x['root_id']==a['root_id']);pk=packets[pid];pi=recode(pid,key)
 rs=[]
 for finding in a['findings']:
  link=links[finding['record_id']];rec=(claims if link['record_kind']=='claim' else chunks)[link['native_id']];pr=next(t for t in pk['records'] if t['record_id']==link['record_id'])
  rs.append(dict(finding=finding,binding=link,record=rec,packet_record=pr))
 aud.append(dict(ticket='A'+str(j),case=ix[pid],raw=raw[ix[pid]['original_id']],contribution_id=pi,overlay=oldpub[pi],origin=rootmap[a['root_id']],audit=a,records=rs,intended_use=pk['intended_use'],artifacts=pk['artifacts']))
# Only read compact per-query fields while scanning the immutable outcomes DB.
c=sqlite3.connect('file:'+str(R/'research_data/provisional_extension_results_v1_20261101/queries.sqlite')+'?mode=ro',uri=True)
q="""select key,json_extract(body,'$.observation.arm'),json_extract(body,'$.observation.probe_id'),json_extract(body,'$.actual.retrieval.trace.supplied_context') from outcomes where json_extract(body,'$.observation.episode_id')=? and json_extract(body,'$.observation.arm') in ('static','S')"""
rows=list(c.execute(q,(eid,)));by={(arm,pid):(k,ctx) for k,arm,pid,ctx in rows}
choice=next(pid for arm,pid in by if arm=='S' and by[arm,pid][1]!=by['static',pid][1])
selected={arm:json.loads(c.execute('select body from outcomes where key=?',(by[arm,choice][0],)).fetchone()[0]) for arm in ['static','S']}
query=next(q for q in p['queries'] if q['query_id']==choice)
# Include only this one recorded pair, not all outcomes or any identifier secret.
data=dict(episode_id=eid,audits=aud,query=query,actual=selected,
 native_texts={k:v.get('text','') for k,v in (claims|chunks).items()},
 native_bindings={x['native_id']:x for x in links.values()},
 origins=rootmap,source_paths=[str((f/(eid+'.json')).relative_to(R)),str((f/(eid+'.json.gz')).relative_to(R)),'research_data/provisional_extension_results_v1_20261101/queries.sqlite'])
(O/'real_examples.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(audits=[(x['ticket'],x['case']['original_id'],x['audit']['outcome']) for x in aud],query=query['text'],selected={a:selected[a]['actual']['retrieval']['trace']['selected_ids'] for a in selected},judges={a:selected[a]['judge'] for a in selected}),indent=2))
