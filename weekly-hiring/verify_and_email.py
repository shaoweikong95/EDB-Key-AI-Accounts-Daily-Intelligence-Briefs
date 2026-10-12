"""Verify public Cloudflare Pages HTML before sending a Gmail link-only digest."""
import os,sys,time,hashlib,urllib.request,smtplib,ssl
from email.message import EmailMessage
from pathlib import Path
URL="https://edb-key-ai-accounts-daily-intelligence-briefs.pages.dev/weekly-hiring/"
RECIPIENT="shaoweikong@gmail.com"
def verify():
    local=Path("weekly-hiring/index.html").read_bytes()
    expected=hashlib.sha256(local).hexdigest()
    err=None
    # Allow time for async Cloudflare Git deployment, but do not claim success early.
    for attempt in range(48):
        try:
            req=urllib.request.Request(URL,headers={"Cache-Control":"no-cache","User-Agent":"WeeklyHiringAudit/1.0"})
            with urllib.request.urlopen(req,timeout=30) as r:
                body=r.read()
                if r.status!=200:raise ValueError("Cloudflare HTTP "+str(r.status))
                if hashlib.sha256(body).hexdigest()!=expected:raise ValueError("Cloudflare does not yet serve the verified report")
            print("PUBLIC_CLOUDFLARE_VERIFIED",URL,flush=True)
            return
        except Exception as e:
            err=e
            if attempt<47:time.sleep(15)
    raise RuntimeError("Cloudflare verification timed out: "+str(err))
def email():
    sender=os.getenv("GMAIL_SENDER","shaoweikong@gmail.com")
    secret=os.getenv("GMAIL_APP_PASSWORD")
    if not secret:raise RuntimeError("GMAIL_APP_PASSWORD is not configured; verified site live but no email sent")
    msg=EmailMessage()
    msg["Subject"]="Key Account Weekly Trend"
    msg["From"]=sender;msg["To"]=RECIPIENT
    msg.set_content(URL)
    with smtplib.SMTP_SSL("smtp.gmail.com",465,context=ssl.create_default_context(),timeout=30) as client:
        client.login(sender,secret);client.send_message(msg)
    print("WEEKLY_LINK_EMAIL_SENT",RECIPIENT,flush=True)
if __name__=="__main__":
    verify()
    email()
