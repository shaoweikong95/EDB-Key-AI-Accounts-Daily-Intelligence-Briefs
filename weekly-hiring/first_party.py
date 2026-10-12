"""Additional first-party job feeds for the weekly hiring audit."""
import json,re,urllib.request,urllib.parse,time
from html.parser import HTMLParser

def load_json(url):
    err=None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 WeeklyHiringResearch","Accept":"application/json"}),timeout=35) as r:
                if r.status!=200:raise ValueError("HTTP "+str(r.status))
                return json.load(r)
        except Exception as e:
            err=e
            if attempt<3:time.sleep(2**attempt)
    raise RuntimeError(str(err))

def smartrecruiters(slug):
    """Public official SmartRecruiters postings API, mandatory full pagination."""
    board="https://careers.smartrecruiters.com/"+slug
    base="https://api.smartrecruiters.com/v1/companies/"+urllib.parse.quote(slug)+"/postings"
    offset=0;alljobs=[];expected=None
    while True:
        data=load_json(base+"?limit=100&offset="+str(offset))
        postings=data.get("content")
        if not isinstance(postings,list):raise ValueError("SmartRecruiters content[] missing")
        if expected is None:expected=data.get("totalFound")
        if expected is None:raise ValueError("SmartRecruiters totalFound missing")
        for j in postings:
            loc=j.get("location") or {}
            country=loc.get("country") or ""
            location=[loc.get("fullLocation",""),loc.get("city",""),loc.get("region",""),country]
            job_id=str(j["id"]);url=j.get("ref") or "https://jobs.smartrecruiters.com/"+slug+"/"+job_id
            alljobs.append((job_id,url,j["name"],location))
        offset+=len(postings)
        if len(alljobs)>=expected:break
        if not postings:raise ValueError("SmartRecruiters pagination truncated")
        if offset>20000:raise ValueError("SmartRecruiters abnormal page volume")
    if len(alljobs)!=expected:raise ValueError(f"SmartRecruiters total mismatch: {len(alljobs)} vs {expected}")
    return board,alljobs

class ListingLinks(HTMLParser):
    def __init__(self):
        super().__init__();self.links=[];self.href=None;self.bits=[]
    def handle_starttag(self,t,attrs):
        if t=="a":self.href=dict(attrs).get("href");self.bits=[]
    def handle_data(self,data):
        if self.href and data.strip():self.bits.append(data.strip())
    def handle_endtag(self,t):
        if t=="a" and self.href:
            self.links.append((self.href," ".join(self.bits).strip()))
            self.href=None;self.bits=[]

def live_html(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 WeeklyHiringResearch"})
    with urllib.request.urlopen(req,timeout=35) as response:
        if response.status!=200:raise ValueError("HTML HTTP "+str(response.status))
        return response.read().decode("utf-8","replace")

def sakana(slug):
    """Official Sakana AI positions; each individual role is a canonical posting."""
    if slug not in ("core","applied"):raise ValueError("Unknown Sakana board")
    board="https://sakana.ai/careers/" if slug=="core" else "https://sakana.ai/applied-careers/"
    parser=ListingLinks();parser.feed(live_html(board))
    listings=[]
    from urllib.parse import urljoin,urlparse
    for href,title in parser.links:
        absolute=urljoin(board,href)
        parsed=urlparse(absolute)
        if parsed.hostname not in ("sakana.ai","www.sakana.ai"):continue
        if slug=="core":
            if not parsed.path.startswith("/careers/") or parsed.path=="/careers/":continue
        else:
            # Applied Team job pages linked from the team's dedicated careers page
            if not (parsed.path.startswith("/applied-careers/") and parsed.path!="/applied-careers/"):continue
        if not title or len(title)>150:title=parsed.path.strip("/").split("/")[-1].replace("-"," ").title()
        key=parsed.path.rstrip("/")
        listings.append((key,absolute,title,["Tokyo, Japan"]))
    ids={x[0] for x in listings}
    if not listings:raise ValueError("No first-party Sakana role links found; page layout may have changed. Example hrefs="+repr(parser.links[:12]))
    if len(ids)!=len(listings):listings=list({x[0]:x for x in listings}.values())
    return board,listings
