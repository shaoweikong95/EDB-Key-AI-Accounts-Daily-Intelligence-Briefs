"""Render immutable weekly hiring snapshot from independently validated ATS audit.

Run only after collect.py emits both audit.json and validated.json.
The renderer never changes the existing root daily intelligence site.
"""
import json,html,sys
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone
from importlib.machinery import SourceFileLoader

HERE=Path(__file__).resolve().parent
model=SourceFileLoader("canonical_audit",str(HERE/"canonical_audit.py")).load_module()
CATEGORIES=model.CATEGORIES
FLAGS={"Singapore":"sg","United States":"us","United Kingdom":"gb","Japan":"jp","France":"fr","Germany":"de","Canada":"ca","India":"in","Australia":"au","China":"cn","Czechia":"cz","Israel":"il","South Korea":"kr","Philippines":"ph","Netherlands":"nl","Switzerland":"ch","Sweden":"se","Ireland":"ie","Spain":"es","Italy":"it","Poland":"pl","United Arab Emirates":"ae","Saudi Arabia":"sa","Taiwan":"tw","Hong Kong":"hk","Brazil":"br","Mexico":"mx","Argentina":"ar","Costa Rica":"cr","Serbia":"rs","Malaysia":"my","Indonesia":"id","Thailand":"th","Vietnam":"vn","New Zealand":"nz","Belgium":"be","Denmark":"dk","Norway":"no","Finland":"fi","Portugal":"pt","Hungary":"hu","Romania":"ro","Turkey":"tr","South Africa":"za"}
COLORS=["#0072B2","#E69F00","#009E73","#CC79A7","#56B4E9","#D55E00","#F0E442","#000000","#5D7088"]
def h(s):return html.escape(str(s),quote=True)
def main():
    src=Path(sys.argv[1]) if len(sys.argv)>1 else Path("weekly-hiring-output")
    target=Path(sys.argv[2]) if len(sys.argv)>2 else Path("weekly-hiring-output/index.html")
    audit=json.loads((src/"audit.json").read_text())
    verified=json.loads((src/"validated.json").read_text())
    statuses=audit["coverage"]
    if len(statuses)!=40 or set(statuses)!=set(model.ACCOUNTS):
        raise ValueError("Incomplete account scope")
    # Re-validate the canonical audit, including 25% fail-safe, before templating
    postings=[model.Posting(**p) for p in audit["postings"]]
    failures={a:str(audit["diagnostics"][a]) for a in model.ACCOUNTS if statuses[a]=="Unverified"}
    sg_ver={a for a in model.ACCOUNTS if statuses[a] in ("Complete","Partial")}
    calc=model.gate(postings,statuses,failures,sg_ver)
    if calc["singapore_total"]!=verified["singapore_total"] or calc["singapore_by_account"]!=verified["singapore_by_account"]:
        raise ValueError("Snapshot aggregate mismatch; refusing to render")
    if calc["country_matrix"]!=verified["country_matrix"]:
        raise ValueError("Country category matrix mismatch")
    byaccount=defaultdict(list); boards=defaultdict(list)
    for p in postings:
        byaccount[p.account].append(p)
        if p.source_board_url not in boards[p.account]:boards[p.account].append(p.source_board_url)
    snapshot_date=datetime.fromisoformat(audit["as_of_utc"].replace("Z","+00:00")).strftime("%d %b %Y %H:%M UTC")
    allcat=Counter(p.category for p in postings if "Singapore" in p.countries)
    maxcount=max(allcat.values(),default=1) or 1
    bars="".join('<div class="barline"><span>'+h(cat)+'</span><div class="bartrack"><div class="barfill" style="width:'+str(round(100*allcat[cat]/maxcount,2))+'%;background:'+COLORS[i]+'"></div></div><b>'+str(allcat[cat])+'</b></div>' for i,cat in sorted(enumerate(CATEGORIES),key=lambda z:(-allcat[z[1]],z[0])))
    lines=[]
    for a in model.ACCOUNTS:
        st=statuses[a]
        counts=calc["singapore_by_account"].get(a)
        sg_count=sum(counts.values()) if counts else None
        posts=byaccount[a]
        global_count=len(posts) if st=="Complete" else None
        if sg_count is None:
            cells="".join('<td class="unknown">—</td>' for _ in CATEGORIES)
        else:
            maximum=max(counts.values());minimum=min(counts.values())
            cells=""
            for c in CATEGORIES:
                v=counts[c]
                cl=(" high" if v==maximum and v!=minimum else " low" if v==minimum and v!=maximum else "")
                cells+='<td class="numeric'+cl+'">'+str(v)+'</td>'
        links=boards.get(a,[])
        title=h(a)
        if links:title='<a rel="noopener noreferrer" target="_blank" href="'+h(links[0])+'">'+title+'</a>'
        if len(links)>1:title+=' <span class="muted small">('+', '.join('<a href="'+h(u)+'" target="_blank" rel="noopener noreferrer">'+h(u.split("/")[2])+'</a>' for u in links[1:])+')</span>'
        roles=[p for p in posts if "Singapore" in p.countries]
        roles=sorted(roles,key=lambda p:(p.category,p.title))[:3]
        previews='<div class="positions">'+(', '.join('<a target="_blank" rel="noopener noreferrer" href="'+h(p.canonical_url)+'">'+h(p.title)+'</a>' for p in roles) if roles else ('No Singapore openings identified on enumerated board' if counts is not None and sg_count==0 else 'Not independently verified'))+'</div>'
        summary='<div class="rowname">'+title+'</div>'+previews
        lines.append('<tr><td class="account">'+summary+'</td>'+cells+'<td class="numeric strong">'+(str(sg_count) if sg_count is not None else '—')+'</td><td class="numeric">'+(str(global_count) if global_count is not None else '—')+'</td><td class="status">'+h(st)+'</td></tr>')
    countries=verified["country_matrix"]
    matrix=[]
    for country in sorted(countries,key=lambda s:(s!="Singapore",s)):
        v=countries[country]
        if not sum(v.values()):continue
        code=FLAGS.get(country)
        flag=('<img loading="lazy" class="flag" alt="" src="https://flagcdn.com/w20/'+code+'.png">' if code else '')
        cells="".join('<td class="numeric">'+str(v[c])+'</td>' for c in CATEGORIES)
        matrix.append('<tr><td>'+flag+h(country)+'</td>'+cells+'<td class="numeric strong">'+str(sum(v.values()))+'</td></tr>')
    head=''.join('<th>'+h(c)+'</th>' for c in CATEGORIES)
    style="""
:root{color-scheme:light;font-family:system-ui,-apple-system,Segoe UI,Arial,sans-serif;color:#16283a;background:#f4f7fa}
*{box-sizing:border-box}body{margin:0}.shell{max-width:1650px;margin:auto;padding:36px 28px}
header{margin:0 0 24px}h1{margin:0;font-size:28px;letter-spacing:-.5px}
.subtitle{margin-top:8px;color:#536779;font-size:14px}
.stats{display:flex;flex-wrap:wrap;gap:16px;margin:20px 0}.stat{background:white;border:1px solid #dae3eb;padding:17px 22px;min-width:170px;border-radius:10px}.stat b{display:block;font-size:26px}
.card{background:white;border:1px solid #dae3eb;border-radius:10px;padding:20px;margin-top:20px;overflow:hidden}
h2{font-size:19px;margin:0 0 13px}.tablewrap{overflow-x:auto}table{border-collapse:separate;border-spacing:0;min-width:1020px;width:100%;font-size:12px}
th{position:sticky;top:0;text-align:center;background:#193e5a;color:white;padding:10px 7px;white-space:nowrap;font-weight:650}
th:first-child{text-align:left}td{border-bottom:1px solid #ebeff2;padding:11px 8px;vertical-align:top}.account{min-width:250px;max-width:340px}.rowname{font-weight:650;font-size:13px}.positions{font-size:11px;line-height:1.65;margin-top:5px;color:#5d6c7b}.numeric{text-align:center;font-variant-numeric:tabular-nums}.strong{font-weight:800}.high{background:#c7f4df}.low{background:#fbe0e1}.unknown{color:#98a2ad;text-align:center}.status{white-space:nowrap;color:#334a63}a{color:#0869ac;text-decoration:none}a:hover{text-decoration:underline}.small{font-size:10px}.muted{color:#64748b}
.barline{display:grid;grid-template-columns:130px 1fr 35px;align-items:center;gap:12px;margin:13px 0;font-size:13px}.bartrack{height:19px;background:#edf1f4;border-radius:3px;overflow:hidden}.barfill{height:100%;min-width:2px}.flag{width:18px;height:13px;object-fit:cover;margin-right:7px;vertical-align:middle;border:1px solid #ddd}
.note{font-size:12px;line-height:1.6;color:#556b7b}.foot{padding:24px 0;color:#738294;font-size:12px}
"""
    doc='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Key Account Weekly Hiring Dashboard</title><style>'''+style+'''</style></head>
<body><div class="shell"><header><h1>Key Account Weekly Hiring Dashboard</h1>
<p class="subtitle">Verified first-party job boards · Snapshot '''+h(snapshot_date)+''' · Singapore job categories</p></header>
<div class="stats"><div class="stat"><span>Singapore postings</span><b>'''+str(verified["singapore_total"])+'''</b></div><div class="stat"><span>Account scope</span><b>40</b></div><div class="stat"><span>Verified boards</span><b>'''+str(sum(st!="Unverified" for st in statuses.values()))+'''</b></div></div>
<section class="card"><h2>Account hiring overview</h2><p class="note">Counts are unique job IDs explicitly tagged Singapore on currently enumerated first-party boards. Highest category per row is green, lowest is red; each cell also displays its numeric count. Dashes mean unverified, not zero. Global totals appear only when global locations are verified.</p><div class="tablewrap"><table><thead><tr><th>Account / Top 3 SG openings</th>'''+head+'''<th>SG Total</th><th>Global Total</th><th>Coverage</th></tr></thead><tbody>'''+''.join(lines)+'''</tbody></table></div></section>
<section class="card"><h2>Singapore openings by job category</h2>'''+bars+'''</section>
<section class="card"><h2>Country × Job Category Matrix</h2><p class="note">Each multi-location job is counted once per country. Only explicit or unambiguous country locations are included; unresolvable regions are not inferred as Singapore. Historic snapshots must be compared using their respective as-of dates.</p><div class="tablewrap"><table><thead><tr><th>Country</th>'''+head+'''<th>Country Total</th></tr></thead><tbody>'''+''.join(matrix)+'''</tbody></table></div></section>
<div class="foot">Source: live first-party hiring boards. Job-level evidence and failure diagnostics are archived by GitHub Actions. No search-engine estimates or cached listings are used.</div></div></body></html>'''
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(doc)
    print("RENDERED",target,verified["singapore_total"],flush=True)
if __name__=="__main__":main()
