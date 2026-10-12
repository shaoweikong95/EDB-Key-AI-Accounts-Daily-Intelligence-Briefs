"""Live first-party ATS collection. Configuration requires VERIFIED board URLs.
Run: python weekly-hiring/collect.py weekly-hiring/boards.json
Produces immutable audit and diagnostics artifacts; never publishes on failure.
"""
import json,sys,time,urllib.request,urllib.error,re
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlparse,quote
from importlib.machinery import SourceFileLoader

audit=SourceFileLoader("canonical_audit",str(Path(__file__).with_name("canonical_audit.py"))).load_module()
CATEGORIES=audit.CATEGORIES

def fetch(url):
    last=None
    for n in range(4):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"WeeklyHiringAudit/1.0","Accept":"application/json"})
            with urllib.request.urlopen(req,timeout=35) as r:
                if r.status!=200: raise ValueError(f"HTTP {r.status}")
                return json.load(r)
        except (Exception) as e:
            last=e
            if n<3: time.sleep(min(2**n,8))
    raise RuntimeError(str(last))

def category(title):
    t=title.lower()
    for name,keys in [
        ("Policy",["policy","government affairs","public affairs"]),
        ("Research",["research","scientist"]),
        ("Applied AI",["applied ai","machine learning","ml engineer","ai engineer","solutions architect"]),
        ("Engineering",["engineer","developer","infrastructure","security","site reliability"]),
        ("Product",["product","design","ux"]),
        ("Sales",["sales","account executive","account manager"]),
        ("GTM",["gtm","growth","partnership","customer success","business development"]),
        ("Marketing",["marketing","brand","communications"]),
        ("Corporate",["finance","legal","people","recruit","operations","chief of staff","hr"])]:
        if any(k in t for k in keys): return name
    return "Corporate"

def locations(value):
    # Resolve only countries explicitly stated by the live ATS location fields
    # or unambiguous named cities/states. Do not treat worldwide/remote as SG.
    if isinstance(value,list): raw=" | ".join(str(x) for x in value if x)
    else: raw=str(value or "")
    geography={
        "Singapore":["Singapore"],
        "United States":["United States","USA","U.S.A.","US Remote","USA - Remote",
            "United States - Remote","San Francisco","New York","Seattle",
            "California","Austin","Denver","Chicago","Boston","Palo Alto","Mountain View",
            "Redwood City","Los Angeles","Memphis","Hawthorne","Starbase","Cape Canaveral",
            "Redmond","Washington DC","Dallas","Miami","Atlanta","Ann Arbor","Portland",
            "Philadelphia","Salt Lake City","Bellevue","Sunnyvale","Southaven"],
        "United Kingdom":["United Kingdom","UK","London","Cambridge, UK","Manchester","Oxford"],
        "Japan":["Japan","Tokyo","Osaka"],
        "France":["France","Paris","Lyon"],
        "Germany":["Germany","Berlin","Munich","Frankfurt","Hamburg"],
        "Canada":["Canada","Toronto","Montreal","Vancouver","Ontario, CAN","British Columbia"],
        "India":["India","Bangalore","Bengaluru","Hyderabad","Mumbai","Gurgaon","Pune","Delhi"],
        "Australia":["Australia","Sydney","Melbourne","Brisbane"],
        "China":["China","Beijing","Shanghai","Shenzhen","Guangzhou"],
        "Czechia":["Czechia","Prague"],
        "Israel":["Israel","Tel Aviv"],
        "South Korea":["South Korea","Seoul"],
        "Philippines":["Philippines","Manila","Makati","Cebu","Alabang"],
        "Netherlands":["Netherlands","Amsterdam"],
        "Switzerland":["Switzerland","Zurich"],
        "Sweden":["Sweden","Stockholm"],
        "Ireland":["Ireland","Dublin"],
        "Spain":["Spain","Madrid","Barcelona"],
        "Italy":["Italy","Milan","Rome"],
        "Poland":["Poland","Warsaw","Krakow"],
        "United Arab Emirates":["United Arab Emirates","Dubai","Abu Dhabi","UAE"],
        "Saudi Arabia":["Saudi Arabia","Riyadh","KSA"],
        "Taiwan":["Taiwan","Taipei"],
        "Hong Kong":["Hong Kong"],
        "Brazil":["Brazil","Sao Paulo","São Paulo"],
        "Mexico":["Mexico","Mexico City"],
        "Argentina":["Argentina","Buenos Aires"],
        "Costa Rica":["Costa Rica","Heredia"],
        "Serbia":["Serbia","Belgrade"],
        "Malaysia":["Malaysia","Kuala Lumpur"],
        "Indonesia":["Indonesia","Jakarta"],
        "Thailand":["Thailand","Bangkok"],
        "Vietnam":["Vietnam","Ho Chi Minh","Hanoi"],
        "New Zealand":["New Zealand","Auckland"],
        "Belgium":["Belgium","Brussels"],
        "Denmark":["Denmark","Copenhagen"],
        "Norway":["Norway","Oslo"],
        "Finland":["Finland","Helsinki"],
        "Portugal":["Portugal","Lisbon"],
        "Hungary":["Hungary","Budapest"],
        "Romania":["Romania","Bucharest"],
        "Turkey":["Turkey","Istanbul"],
        "Türkiye":["Türkiye"],
        "South Africa":["South Africa","Cape Town","Johannesburg"],
    }
    matches=[]
    for country,terms in geography.items():
        for token in terms:
            if re.search(r"(?<![A-Za-z])"+re.escape(token)+r"(?![A-Za-z])",raw,re.I):
                matches.append(country);break
    if "Türkiye" in matches:
        matches=[x for x in matches if x!="Türkiye"]+["Turkey"]
    return tuple(dict.fromkeys(matches))

def collect_one(config):
    kind=config["ats"]; slug=config["slug"]; account=config["account"]
    if kind=="greenhouse":
        board=f"https://boards.greenhouse.io/{slug}"
        data=fetch(f"https://boards-api.greenhouse.io/v1/boards/{quote(slug)}/jobs?content=true")
        jobs=data["jobs"]
        if "meta" in data and "total" in data["meta"] and data["meta"]["total"]!=len(jobs):
            raise ValueError("Greenhouse board total mismatch")
        mapped=[(str(j["id"]),j["absolute_url"],j["title"],
                 [j.get("location",{}).get("name","")]+[o.get("name","") for o in j.get("offices",[])]) for j in jobs]
    elif kind=="lever":
        board=f"https://jobs.lever.co/{slug}"
        jobs=fetch(f"https://api.lever.co/v0/postings/{quote(slug)}?mode=json")
        mapped=[(str(j["id"]),j["hostedUrl"],j["text"],
                 [j.get("categories",{}).get("location","")]+j.get("categories",{}).get("allLocations",[])) for j in jobs]
    elif kind=="ashby":
        board=f"https://jobs.ashbyhq.com/{slug}"
        data=fetch(f"https://api.ashbyhq.com/posting-api/job-board/{quote(slug)}")
        jobs=[j for j in data["jobs"] if j.get("isListed",True)]
        mapped=[(str(j["id"]),j["jobUrl"],j["title"],
                 [j.get("location","")]+[x.get("location","") for x in j.get("secondaryLocations",[])]) for j in jobs]
    else: raise ValueError("Unsupported ATS")
    if len({j[0] for j in mapped})!=len(mapped): raise ValueError("Duplicate IDs from ATS")
    postings=[]
    unresolved=[]
    for job_id,url,title,loc in mapped:
        countries=locations(loc)
        if not countries:
            unresolved.append({"job_id":job_id,"location_metadata":loc})
        postings.append(audit.Posting(account,config.get("entity",account),job_id,url,title,category(title),countries,board,tuple(str(x) for x in loc if x)))
    return board,postings,unresolved,len(mapped)

def main():
    config=json.loads(Path(sys.argv[1]).read_text())
    names=[c["account"] for c in config]
    unique_boards=[(c["account"],c.get("entity",c["account"]),c["ats"],c["slug"]) for c in config]
    if len(unique_boards)!=len(set(unique_boards)): raise ValueError("Duplicate entity/ATS/board config")
    result=[]; diagnostics={}; coverage={}; verified=set()
    for account in audit.ACCOUNTS:
        configs=[c for c in config if c["account"]==account]
        if not configs:
            coverage[account]="Unverified";diagnostics[account]="No verified ATS board configured";continue
        try:
            alljobs=[];missing=[];totals=[]
            for c in configs:
                board,jobs,unresolved,total=collect_one(c)
                alljobs+=jobs;missing+=unresolved;totals.append(total)
            if len({(p.entity,p.job_id) for p in alljobs})!=len(alljobs):
                raise ValueError("Duplicate IDs across boards")
            status="Partial" if missing else "Complete"
            result+=alljobs;verified.add(account);coverage[account]=status
            diagnostics[account]={"board_jobs":sum(totals),"canonical_jobs":len(alljobs),
                 "unresolved_country_count":len(missing),"unresolved_examples":missing[:5],"status":status}
        except Exception as e:
            coverage[account]="Unverified";diagnostics[account]=str(e)
    out=Path("weekly-hiring-output");out.mkdir(exist_ok=True)
    timestamp=datetime.now(timezone.utc).isoformat()
    payload={"as_of_utc":timestamp,"coverage":coverage,"diagnostics":diagnostics,
             "postings":[vars(p) for p in result]}
    (out/"audit.json").write_text(json.dumps(payload,indent=2))
    try:
        # Every unverified account has diagnostics; no fabricated zero.
        summary=audit.gate(result,coverage,{a:str(diagnostics[a]) for a in audit.ACCOUNTS if coverage[a]=="Unverified"},verified)
        (out/"validated.json").write_text(json.dumps({"as_of_utc":timestamp,"coverage":coverage,
             "singapore_total":summary["singapore_total"],
             "singapore_by_account":summary["singapore_by_account"],"country_matrix":summary["country_matrix"]},indent=2))
        print("VALIDATED",summary["singapore_total"])
    except Exception as e:
        (out/"validation_failure.txt").write_text(str(e))
        print("VALIDATION FAILED:",e)
        sys.exit(2)

if __name__=="__main__": main()
