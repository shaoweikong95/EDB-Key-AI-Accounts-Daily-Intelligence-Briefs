"""Atomic, date-keyed Google Sheets baseline upsert, gated by verified audit.

Requires GOOGLE_SERVICE_ACCOUNT_JSON in a GitHub Actions secret, with Editor access
to the existing Google Sheet. No write is attempted without validated.json.
Never delete historical rows.
"""
import json,os,re,sys,urllib.parse,urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from importlib.machinery import SourceFileLoader

HERE=Path(__file__).resolve().parent
model=SourceFileLoader("canonical_audit",str(HERE/"canonical_audit.py")).load_module()
SHEET_ID="1FeJ5MHieKO7dfAhCVxfp4yiQKI2QgXQxyV5eCEtxsiY"
SHEET_TITLE="Weekly Baseline"
EXPECTED=["Snapshot Date","Account",*model.CATEGORIES,"SG Total","Global Total","Coverage Status"]

def credentials():
    if not os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"):
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON secret is not configured; Google Sheet unchanged")
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    info=json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    cred=service_account.Credentials.from_service_account_info(info,scopes=["https://www.googleapis.com/auth/spreadsheets"])
    cred.refresh(Request())
    return cred.token

def api(token,method,endpoint,payload=None):
    base="https://sheets.googleapis.com/v4/spreadsheets/"+SHEET_ID
    url=base+endpoint
    data=json.dumps(payload).encode() if payload is not None else None
    req=urllib.request.Request(url,data=data,method=method,headers={"Authorization":"Bearer "+token,
        "Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=60) as response:
        return json.load(response)

def rowvalue(v):
    if v is None:return {}
    if isinstance(v,(int,float)):return {"userEnteredValue":{"numberValue":v}}
    if isinstance(v,str) and v.startswith("=HYPERLINK("):return {"userEnteredValue":{"formulaValue":v}}
    return {"userEnteredValue":{"stringValue":str(v)}}

def launch():
    source=Path(sys.argv[1]) if len(sys.argv)>1 else Path("weekly-hiring-output")
    audit=json.loads((source/"audit.json").read_text())
    validated=json.loads((source/"validated.json").read_text())
    statuses=audit["coverage"]
    posts=[model.Posting(**p) for p in audit["postings"]]
    failures={a:str(audit["diagnostics"][a]) for a in model.ACCOUNTS if statuses[a]=="Unverified"}
    sgverified={a for a in model.ACCOUNTS if statuses[a]!="Unverified"}
    result=model.gate(posts,statuses,failures,sgverified)
    if result["singapore_total"]!=validated["singapore_total"]:
        raise ValueError("Validated report data changed, write blocked")
    if result["singapore_by_account"]!=validated["singapore_by_account"]:
        raise ValueError("Validated per-account matrix changed, write blocked")
    today=datetime.fromisoformat(audit["as_of_utc"].replace("Z","+00:00")).astimezone(
        __import__("zoneinfo").ZoneInfo("Asia/Singapore")).strftime("%Y-%m-%d")
    byaccount=defaultdict(list);boards={}
    for p in posts:
        byaccount[p.account].append(p)
        boards.setdefault(p.account,p.source_board_url)
    prepared={}
    for name in model.ACCOUNTS:
        status=statuses[name]
        sg=result["singapore_by_account"].get(name)
        sg_total=sum(sg.values()) if sg is not None else None
        global_total=len(byaccount[name]) if status=="Complete" else None
        board=boards.get(name)
        if status!="Unverified" and not board:raise ValueError("Missing verified board URL "+name)
        account_cell='=HYPERLINK("'+board.replace('"','""')+'","'+name.replace('"','""')+'")' if board else name
        prepared[name]=[today,account_cell,*([sg[c] for c in model.CATEGORIES] if sg else [None]*9),
                        sg_total,global_total,status]
    token=credentials()
    meta=api(token,"GET","?fields=sheets(properties),spreadsheetId")
    ids=[i["properties"] for i in meta["sheets"] if i["properties"]["title"]==SHEET_TITLE]
    if len(ids)!=1:raise ValueError("Cannot uniquely identify Weekly Baseline")
    props=ids[0];sheet_id=props["sheetId"]
    rectangle="'Weekly Baseline'!A1:N1000"
    response=api(token,"GET","/values/"+urllib.parse.quote(rectangle,safe="!':")+
                 "?valueRenderOption=FORMATTED_VALUE")
    existing=response.get("values",[])
    if not existing or existing[0][:13]!=EXPECTED[:13] or (len(existing[0])>=14 and existing[0][13] not in ("",EXPECTED[13])):
        raise ValueError("Header format changed; baseline was not modified")
    lookup={}
    for i,line in enumerate(existing[1:],start=1):
        if len(line)>1 and line[0] and line[1]:
            key=(line[0],line[1])
            if key in lookup:raise ValueError("Ambiguous historical duplicate date/account")
            lookup[key]=i
    last=max([i for i,line in enumerate(existing) if any(str(x).strip() for x in line)],default=0)
    updates=[]
    # Add Coverage Status header only if it is absent, preserve A:M and history.
    if len(existing[0])<14:
        updates.append({"updateCells":{"range":{"sheetId":sheet_id,"startRowIndex":0,"endRowIndex":1,
                          "startColumnIndex":13,"endColumnIndex":14},
                        "rows":[{"values":[rowvalue(EXPECTED[13])]}],"fields":"userEnteredValue"}})
    positions={}
    for name in model.ACCOUNTS:
        index=lookup.get((today,name))
        if index is None:
            last+=1;index=last
        positions[name]=index
    need=max(positions.values())+1-props["gridProperties"]["rowCount"]
    if need>0:
        updates.append({"appendDimension":{"sheetId":sheet_id,"dimension":"ROWS","length":need}})
    for name in model.ACCOUNTS:
        index=positions[name]
        updates.append({"updateCells":{"range":{"sheetId":sheet_id,"startRowIndex":index,
            "endRowIndex":index+1,"startColumnIndex":0,"endColumnIndex":14},
            "rows":[{"values":[rowvalue(v) for v in prepared[name]]}],"fields":"userEnteredValue"}})
    api(token,"POST",":batchUpdate",{"requests":updates})
    # Read back live cells, prove exactly one Date+Account row and all value cells match.
    check=api(token,"GET","/values/"+urllib.parse.quote("'Weekly Baseline'!A1:N1000",safe="!':")+
              "?valueRenderOption=UNFORMATTED_VALUE")
    cells=check.get("values",[])
    found={}
    for i,line in enumerate(cells[1:],start=1):
        if len(line)>1 and line[0]==today:
            if line[1] in found:raise ValueError("Duplicate current-date account after upsert")
            found[line[1]]=(i,line)
    if set(found)!=set(model.ACCOUNTS):raise ValueError("Post-write account reconciliation failed")
    for name in model.ACCOUNTS:
        actual=found[name][1];target=prepared[name]
        for c in range(2,14):
            required=target[c];observed=actual[c] if c<len(actual) else None
            if observed in ("",None) and required is None:continue
            if observed!=required:raise ValueError(f"Post-write mismatch {name} column {c}: {observed} vs {required}")
    print("GOOGLE_SHEET_VERIFIED",today,len(found),flush=True)
if __name__=="__main__":launch()
