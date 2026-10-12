"""Build visibly INCOMPLETE preview from live audit even when production gate fails.

Preview must never be placed at the production /weekly-hiring/ path.
It is intentionally not a certified historic weekly snapshot.
"""
from pathlib import Path
from collections import Counter,defaultdict
import json,sys,html
from datetime import datetime
from zoneinfo import ZoneInfo
from importlib.machinery import SourceFileLoader

ROOT=Path(__file__).resolve().parent
spec=SourceFileLoader("canonical_audit",str(ROOT/"canonical_audit.py")).load_module()
CATS=spec.CATEGORIES
COLORS=["#0072B2","#E69F00","#009E73","#CC79A7","#56B4E9","#D55E00","#F0E442","#222222","#5D7088"]
FLAGS={"Singapore":"sg","United States":"us","United Kingdom":"gb","Japan":"jp","France":"fr","Germany":"de","Canada":"ca","India":"in","Australia":"au","China":"cn","Czechia":"cz","Israel":"il","South Korea":"kr","Philippines":"ph","Netherlands":"nl","Switzerland":"ch","Sweden":"se","Ireland":"ie","Spain":"es","Italy":"it","Poland":"pl","United Arab Emirates":"ae","Saudi Arabia":"sa","Taiwan":"tw","Hong Kong":"hk","Brazil":"br","Mexico":"mx","Argentina":"ar","Costa Rica":"cr","Serbia":"rs","Malaysia":"my","Indonesia":"id","Thailand":"th","Vietnam":"vn","New Zealand":"nz","Belgium":"be","Denmark":"dk","Norway":"no","Finland":"fi","Portugal":"pt","Hungary":"hu","Romania":"ro","Turkey":"tr","South Africa":"za"}
def h(s):return html.escape(str(s),quote=True)
def main():
    src=Path(sys.argv[1]) if len(sys.argv)>1 else Path("weekly-hiring-output")
    target=Path(sys.argv[2]) if len(sys.argv)>2 else Path("weekly-hiring-preview/index.html")
    if target.parts[:2]==("weekly-hiring","index.html"):
        raise ValueError("Preview cannot overwrite production hiring dashboard")
    data=json.loads((src/"audit.json").read_text())
    statuses=data["coverage"]
    if len(statuses)!=40 or set(statuses)!=set(spec.ACCOUNTS):
        raise ValueError("Partial preview must enumerate all account coverage states")
    postings=[spec.Posting(**p) for p in data["postings"]]
    seen=set()
    for p in postings:
        key=(p.account,p.entity,p.job_id)
        if key in seen:raise ValueError("Duplicate live posting in preview")
        seen.add(key)
    totals=Counter((p.account,p.category) for p in postings if "Singapore" in p.countries)
    byaccount=defaultdict(list);matrix=Counter()
    for p in postings:
        byaccount[p.account].append(p)
        for country in set(p.countries):matrix[country,p.category]+=1
    timestamp=datetime.fromisoformat(data["as_of_utc"]).astimezone(ZoneInfo("Asia/Singapore")).strftime("%d %b %Y %H:%M SGT")
    head="".join("<th>"+h(c)+"</th>" for c in CATS)
    trs=[]
    for a in spec.ACCOUNTS:
        stat=statuses[a];records=byaccount[a]
        board=records[0].source_board_url if records else ""
        title='<a href="'+h(board)+'" target="_blank" rel="noopener noreferrer">'+h(a)+'</a>' if board else h(a)
        roles=sorted([p for p in records if "Singapore" in p.countries],key=lambda p:(p.category,p.title))[:3]
        titles=" · ".join('<a href="'+h(p.canonical_url)+'" target="_blank" rel="noopener noreferrer">'+h(p.title)+'</a>' for p in roles)
        if stat=="Unverified":
            cells='<td class="missing">—</td>'*9
            sg_count=global_count='<td class="missing">—</td>'
        else:
            nums=[totals[a,c] for c in CATS];top=max(nums);bottom=min(nums)
            cells="".join('<td class="'+("high" if v==top and top!=bottom else "low" if v==bottom and top!=bottom else "")+'">'+str(v)+"</td>" for v in nums)
            sg_count='<td><b>'+str(sum(nums))+"</b></td>"
            global_count='<td>'+str(len(records))+"</td>" if stat=="Complete" else '<td class="missing">—</td>'
        trs.append('<tr><td class="name"><b>'+title+'</b><div class="roles">'+titles+"</div></td>"+cells+sg_count+global_count+"<td>"+h(stat)+"</td></tr>")
    aggregate=Counter(p.category for p in postings if "Singapore" in p.countries)
    maxval=max(aggregate.values(),default=1) or 1
    bars="".join('<div class="bar"><span>'+h(c)+'</span><div class="track"><div style="height:100%;width:'+str(round(100*aggregate[c]/maxval,1))+'%;background:'+COLORS[CATS.index(c)]+'"></div></div><b>'+str(aggregate[c])+"</b></div>" for c in sorted(CATS,key=lambda x:-aggregate[x]))
    flagmatrix=[]
    for c in sorted({country for country,_ in matrix},key=lambda x:(x!="Singapore",x)):
        vs=[matrix[c,cat] for cat in CATS]
        if not sum(vs):continue
        img=('<img loading="lazy" class="flag" alt="" src="https://flagcdn.com/w20/'+FLAGS[c]+'.png">' if c in FLAGS else "")
        flagmatrix.append('<tr><td class="name">'+img+h(c)+'</td>'+''.join("<td>"+str(v)+"</td>" for v in vs)+"<td><b>"+str(sum(vs))+"</b></td></tr>")
    summary=sum(aggregate.values());found=sum(s!="Unverified" for s in statuses.values())
    css="""*{box-sizing:border-box}body{font:14px system-ui,Arial,sans-serif;background:#f4f7fa;color:#1b3245;margin:0}main{max-width:1600px;margin:30px auto;padding:0 25px}h1{font-size:25px}h2{font-size:19px}.banner{background:#fff6df;border-left:6px solid #d18b00;padding:15px 18px;margin:15px 0 24px;border-radius:4px}.card{background:#fff;border-radius:10px;padding:20px;margin:22px 0;border:1px solid #dbe3ed}.muted{color:#5c7286}a{color:#0769ac;text-decoration:none}a:hover{text-decoration:underline}.wrap{overflow:auto}table{min-width:1050px;width:100%;border-collapse:collapse;font-size:12px}th{background:#193e5a;color:#fff;padding:10px 6px;text-align:center;white-space:nowrap}th:first-child{text-align:left}td{padding:10px 7px;border-bottom:1px solid #ecf0f3;text-align:center}td.name{text-align:left;min-width:240px}.roles{font-size:10px;margin-top:4px}.high{background:#c7f4df}.low{background:#fbe0e1}.missing{color:#9ca3af}.bar{display:grid;grid-template-columns:130px 1fr 40px;align-items:center;gap:10px;margin:12px 0}.track{background:#e8edf1;height:21px}.flag{width:20px;vertical-align:middle;margin-right:5px}.meta{display:flex;gap:25px;flex-wrap:wrap}.stat{font-size:23px;font-weight:700}.small{font-size:12px}"""
    page='<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Weekly Hiring — Incomplete Live Preview</title><style>'+css+'</style></head><body><main><h1>Key Account Weekly Hiring Dashboard — Live Extraction Preview</h1><div class="muted">First-party posting audit · '+h(timestamp)+'</div>'
    page+='<div class="banner"><strong>INCOMPLETE — not a validated weekly snapshot.</strong><p>'+str(found)+' of 40 accounts have accessible, enumerated first-party feeds. Singapore figures are observed explicit-location postings, potentially lower bounds if additional location metadata is unresolved. Unverified accounts are blank, never zero. Weekly Baseline remains unchanged until all validation requirements pass.</p></div>'
    page+='<div class="meta"><div><div class="stat">'+str(summary)+'</div><div class="small muted">Observed SG postings</div></div><div><div class="stat">'+str(found)+'/40</div><div class="small muted">Source-enumerated accounts</div></div><div><div class="stat">'+format(len(postings),",")+'</div><div class="small muted">Live audit posting IDs</div></div></div>'
    page+='<section class="card"><h2>Singapore hiring by account</h2><p class="small muted">Green marks category high; red marks low. All numbers come from explicit live job-location metadata.</p><div class="wrap"><table><thead><tr><th>Account · Top 3 SG roles</th>'+head+'<th>Observed SG</th><th>Verified Global</th><th>Coverage</th></tr></thead><tbody>'+''.join(trs)+'</tbody></table></div></section>'
    page+='<section class="card"><h2>Singapore job categories — observed</h2>'+bars+'</section>'
    page+='<section class="card"><h2>Country × category matrix — observed</h2><p class="small muted">Unresolvable regions and location-free postings are excluded; jobs with multiple explicit countries count once per country.</p><div class="wrap"><table><thead><tr><th>Country</th>'+head+'<th>Total</th></tr></thead><tbody>'+''.join(flagmatrix)+'</tbody></table></div></section>'
    page+='<p class="muted small">Job-level evidence and coverage diagnostics archived in the matching GitHub Actions run. This preview is not the official weekly report.</p></main></body></html>'
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(page)
    print("INCOMPLETE_PREVIEW_RENDERED",target,summary,found,flush=True)
if __name__=="__main__":main()
