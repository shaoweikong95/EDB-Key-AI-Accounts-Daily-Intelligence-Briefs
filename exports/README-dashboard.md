# Recreate the 40-Account Daily AI Intelligence Email Dashboard

**Reference export:** [16 October 2026 black-theme HTML](./daily-ai-intelligence-2026-10-16.html)  
**Live dashboard (separate):** https://edb-key-ai-accounts-daily-intelligence-briefs.pages.dev/  
**Status:** The reference HTML is a static archived edition. This guide explains how to reproduce the daily workflow; it does not itself install a scheduler or prove delivery of future messages.

## 1. Requirements

- A Gmail account with permission to send mail to `shaoweikong@gmail.com`.
- A research capability with access to official company newsrooms, credible media, Singapore government releases and dated articles.
- A persistent store (existing: Supabase project `ifadsygimdvzlsgvlzjc`) or equivalent database to store source evidence and past account stories.
- The GitHub repo `shaoweikong95/EDB-Key-AI-Accounts-Daily-Intelligence-Briefs` as a source of account names and baseline historical data.
- A task scheduler to run at **05:00 Asia/Singapore**, and a trusted service that sends an HTML-body email (e.g., authenticated Gmail integration). Merely hosting an HTML file does not schedule or send it.

## 2. Data schema / account coverage

Use exactly 40 unique accounts. Source the canonical list from `legacy/bootstrap-2026-09-27.html` in the repository's embedded `DATA.accounts` array, including `Google DeepMind`. Account-manager groupings are *not displayed* in this email.

Read previously stored evidence from `data/latest.js` (`window.DAILY_BRIEF`) and Supabase, but treat it as historical context, never as proof of fresh news.

Each account record must contain:
- `name`, `headline`, `url`, `source`, `published_date`
- `executive_summary` (fact-grounded)
- `singapore_edb_opportunity` (analysis, clearly distinguished from facts)
- `challenge` (analysis / operational constraint)
- `more_reading`: 0–5 additional distinct entries, each with `headline`, `url`, `source`, `published_date`.

The brief also includes four Overview subsections, two World lead stories, and two APAC/Singapore lead stories, each with a dated source and, where appropriate, executive summary, opportunity, challenge.

## 3. Daily comprehensive research methodology

For **each of the 40 companies**, perform independent targeted searches covering:
1. Company newsroom, releases, product changelog, developer docs and research/blog.
2. Official events, office openings, management appearances and flagship conferences.
3. Government/media releases (especially Singapore MDDI, EDB, MTI, IMDA and credible APAC government sources).
4. Partnerships, customer deployments, investment, funding, financial performance and acquisitions.
5. Hiring, executive appointments, APAC expansion, research, safety, legal and operating issues.

Search the prior **7–14 days** for context alongside the daily news window; don't exclude an important event simply because it occurred more than 24 hours earlier. Example: ElevenLabs' Singapore launch on 8 October 2026 is materially relevant to the 16 October brief.

Rank by strategic **materiality to EDB**, not just publication recency. An office launch, local engineering investment or government agreement usually outranks a generic product mention.

For each claim: record its primary URL, independent confirmation if needed, original publication date, and whether the statement is a company-specific development or broader industry context. Avoid presenting sector news as a company announcement. If no new credible story is found after targeted searches, keep the **latest previously verified company story with its real old date**, and state it is a fallback.

Generate 0–5 More Reading links per account from recent verified evidence (prefer recent five days, broaden to 14 days for material stories). Never invent links, manufacture news or duplicate the leading headline in More Reading.

## 4. Design specification (preserve across editions)

Build an **email-safe HTML document** with inline CSS and nested tables, not JavaScript. Match the supplied reference HTML:
- Page background: `#050505` (black)
- Content/card background: `#10151c`
- Body text: `#eff3fa`
- Secondary text: `#abb8c8`
- Links: `#9cccff`
- Borders: `#354253`
- Arial/Helvetica sans-serif, ~780px maximum content width
- Header: “Key Accounts Daily AI Intelligence Briefs” and the *actual* research cutoff date
- Sections: Overview → World AI Intelligence → APAC & Singapore AI Intelligence → Account Intelligence
- Display all **40 account cards alphabetically A–Z**. Do not display account-manager headings.
- Each card: company name, linked top headline, dated source, Executive Summary, Singapore / EDB Opportunity, Challenge, More Reading.
- **No clickable in-email A–Z index, filtering widgets, `<script>` code or `href="#section"` links.** Gmail may strip/ignore these; use the browser's search/find feature for the long email.

This reference HTML is self-contained and can be reused as a structural template by replacing the news content inside it.

## 5. Quality-control gates before sending

1. All **40 unique** accounts present and ordered A–Z.
2. No duplicates, omitted cards or manager labels.
3. Four Overview themes, World and APAC/Singapore lead stories complete.
4. Every account has a headline, real URL, published date, executive summary, opportunity and challenge.
5. Every More Reading URL is relevant, dated, deduplicated and distinct from the lead item.
6. The brief correctly marks older fallback stories instead of implying all 40 received brand-new news.
7. Confirm source URLs exist/resolve as appropriate, and scan high-impact stories against first-party sources.
8. Inspect the HTML email in Gmail, including mobile widths, black background and legible links.
9. Confirm actual send via Gmail's successful send result; do not call a prepared draft “sent.”

## 6. Daily automation

Configure your scheduler for:

```ics
BEGIN:VEVENT
DTSTART;TZID=Asia/Singapore:20261024T050000
RRULE:FREQ=DAILY;BYHOUR=5;BYMINUTE=0;BYSECOND=0
END:VEVENT
```

Each scheduled execution must: load previous evidence → research and corroborate news → deduplicate/persist articles → build full 40-account content → render HTML preserving format → validate QA gates → send HTML in Gmail body to `shaoweikong@gmail.com` → record send result and errors.

A failed research, export or Gmail stage must be reported distinctly. Retries should preserve verified evidence and avoid duplicate sends. Use an idempotency key based on `brief_date + recipient` to detect successful previous delivery.

## 7. Key caveats

- **Filtering inside Gmail:** Reliable, functional JavaScript filters are not supported in ordinary Gmail HTML email. For true search/filter widgets, retain a separately hosted dashboard linked from the email; do not make the email dependent on it.
- **One-off export:** The file `daily-ai-intelligence-2026-10-16.html` is an archived snapshot. It will not refresh itself and should never be automatically relabelled with a later date.
- **Evidence quality:** Extensive searches improve coverage but cannot guarantee that every private, unannounced or paywalled development will be found. State coverage limitations accurately.
