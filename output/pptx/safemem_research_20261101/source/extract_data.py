"""Read-only, offline extraction for the editable research presentation."""
import gzip
import hashlib
import json
from pathlib import Path
from ams.research.dynamic.ledger import EvidenceSnapshot, LedgerConfig
from ams.research.dynamic.models import parse_event

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).parent
def read(p): return json.loads((ROOT / p).read_text())
tables = read('output/pdf/research_result_tables_20261101/source_data.json')['tables']
comparison = read('research_data/development_comparison_report_v1_20261101/comparison.json')
base = ROOT / 'research_data/mpbench_provisional_v1_20261029'
index = json.loads((base / 'private/episode_index.json').read_text())
conditions = []
for scenario in ['strong_distributed', 'strong_localized', 'uninformative']:
    ix = next(x for x in index if x['bag_id'] == 'D01' and x['scenario'] == scenario)
    pub = json.loads((base / ix['public_file']).read_text())
    prv = json.loads((base / ix['private_file']).read_text())
    overlay = pub['overlay']
    users = sorted({v['contributor_id'] for v in overlay.values()})
    rows = []
    for ctx in ['email', 'file_and_doc']:
        for ui, u in enumerate(users):
            bs = sorted({v['batch_id'] for v in overlay.values() if v['context_id']==ctx and v['contributor_id']==u})
            for bi, b in enumerate(bs):
                ids = sorted(k for k,v in overlay.items() if v['context_id']==ctx and v['contributor_id']==u and v['batch_id']==b)
                rows.append(dict(context=ctx, user=ui+1, batch=bi+1, batch_id=b,
                    ids=ids, attack=[prv['case_labels'][k] for k in ids]))
    conditions.append(dict(scenario=scenario, rows=rows, public_path=ix['public_file'], private_path=ix['private_file']))
eid='ep_43547fc840a2c88dacd18bd7'
f=ROOT/'research_data/provisional_extension_freeze_v1_20261101/private'
private=json.loads((f/(eid+'.json')).read_text())
snap=json.load(gzip.open(f/(eid+'.json.gz'),'rt'))['evidence']
ev=tuple(parse_event(x) for x in snap['events'])
config=LedgerConfig(**snap['config'])
initial=EvidenceSnapshot(config, ev, snap['as_of'])
root=initial.roots[private['audits'][0]['root_id']]
trace=[]
for j,a in enumerate(private['audits']):
    ev += (parse_event(a),)
    view=EvidenceSnapshot(config,ev,a['revealed_at'])
    o=view.roots[a['root_id']]
    trace.append(dict(ticket='A'+str(j), outcome=a['outcome'], context=o.context_id,
       same_batch_as_root=o.batch_id==root.batch_id,
       counts={g:dict(unsafe=view.group(g,root.contributor_id,root.context_id,root.batch_id).unsafe,
                      safe=view.group(g,root.contributor_id,root.context_id,root.batch_id).safe,
                      penalty=float(view.group(g,root.contributor_id,root.context_id,root.batch_id).penalty)) for g in ['batch','context','source']},
       active_scopes=list(view.active_scopes(root))))
example_path=ROOT/'data/mpbench/adversarial_data.jsonl.jsonl'
example=json.loads(example_path.open().readline())
sources=['README.md','reports/RESEARCH_AUDIT_20261101_REPORT.md',
 'reports/PROVISIONAL_RESULTS_20261101_REPORT.md','reports/RECOVERY_20261029_REPORT.md',
 'reports/MPBENCH_DYNAMIC_EXPERIMENT_PROTOCOL.md','reports/PROVISIONAL_20261029_DESIGN.md',
 'reports/safemem_full_mpbench/RUN_REPORT.md',
 'research_data/development_comparison_report_v1_20261101/comparison.json',
 'src/ams/research/dynamic/ledger.py','src/ams/research/dynamic/policies.py',
 'src/ams/research/retrieval/adapter.py','src/ams/research/retrieval/metadata.py',
 'src/ams/research/provisional/episodes.py','src/ams/research/sequential/state.py',
 'src/ams/research/sequential/runner.py','src/ams/research/provisional_extension.py',
 'src/ams/research/provisional_run/preparation.py','safe-mem_paper.pdf']
hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources}
data=dict(tables=tables, conditions=conditions, audit_trace=trace, example=example,
          comparison=comparison, source_sha256=hashes,
          audit_trace_source=str((f/(eid+'.json')).relative_to(ROOT)))
(OUT/'verified_data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(example_id=example['id'],audit_trace=trace,condition_attack_counts=[sum(sum(r['attack']) for r in c['rows']) for c in conditions]),indent=2))
