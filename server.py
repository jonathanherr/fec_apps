"""FEC x Jev head-to-head server. Stdlib only (Python 3.9+). Keys stay server-side."""
import json
import os
import threading
import time
import traceback
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("FECJEV_PORT", "8741"))

FEC_BASE = "https://api.open.fec.gov/v1"
JEV_URL = "https://api.typesafe.ai/v1/systemone"

TACTICS = ["media", "direct_contact", "operations", "transfers",
           "legal_compliance", "fundraising_ops", "events"]

TACTIC_CRITERIA = {
    "media": "Paid advertising and its production: media buys, placed media, digital consulting, video production, online advertising, communications/digital consulting for messaging",
    "direct_contact": "Direct voter contact: mail, postage, phones, telemarketing, canvassing, palm cards, yard signs, email outreach",
    "fundraising_ops": "Fundraising costs and payment processing: credit card payments, merchant/service/bank fees, refunds",
    "transfers": "Money leaving to other committees: contributions, donations, transfers",
    "legal_compliance": "Legal, compliance, polling, taxes, payroll taxes, political/strategy/research/communications consulting",
    "operations": "Staff and admin overhead: payroll, rent, travel, lodging, security, IT, software, data services, office equipment",
    "events": "In-person events and rallies: event staging, audiovisual for events, facility rental, catering, event broadcasting, event security",
}

SECTOR_CRITERIA = {
    "retired_not_employed": "Retired, not employed, homemaker, or no occupation given",
    "legal": "Attorneys, lawyers, legal professionals",
    "education": "Professors, teachers, academics",
    "health": "Doctors, nurses, therapists, social workers, health care",
    "business_exec": "CEO, executives, entrepreneurs, investors, business owners, consultants",
    "technical": "Engineers, technical professionals",
    "arts_media": "Producers, artists, media, entertainment",
    "admin_service": "Secretaries, admin, corrections, other service workers",
    "unknown": "Cannot determine or information requested/missing",
}


def load_env(path):
    env = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


ENV = load_env(os.path.join(HERE, ".env"))
FEC_KEY = ENV["FEC_API_KEY"]
JEV_KEY = ENV["JEV_KEY"]

with open(os.path.join(HERE, "presets.json")) as f:
    PRESETS = json.load(f)

LOCK = threading.Lock()


def load_cache(name):
    with open(os.path.join(HERE, name)) as f:
        return json.load(f)


def save_cache(name, data):
    with LOCK:
        with open(os.path.join(HERE, name), "w") as f:
            json.dump(data, f, indent=1)


TACTIC_CACHE = load_cache("tactic_cache.json")
SECTOR_CACHE = load_cache("sector_cache.json")
try:
    NAMES_CACHE = load_cache("committee_names.json")
except IOError:
    NAMES_CACHE = {}

JOBS = {}


def fec(path, params, tries=5):
    params = dict(params)
    params["api_key"] = FEC_KEY
    for i in range(tries):
        try:
            url = FEC_BASE + path + "?" + urllib.parse.urlencode(params)
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except Exception as e:
            if i == tries - 1:
                raise
            time.sleep(3 * (i + 1))


def jev(state, questions, tries=4):
    body = json.dumps({"state": state, "model": "jev-latest",
                       "questions": questions}).encode()
    for i in range(tries):
        try:
            req = urllib.request.Request(
                JEV_URL, data=body,
                headers={"Authorization": "Bearer " + JEV_KEY,
                         "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(3 * (i + 1))


def jev_classify(items, criteria, key_prefix):
    """One batched call: N parallel Choice questions. Returns {item: (label, conf)}."""
    state = {"items": [{"id": i, "text": t} for i, t in enumerate(items)]}
    questions = {
        "%s%d" % (key_prefix, i): {
            "type": "choice",
            "instructions": ("Which category best describes `items[%d].text`? "
                             "Reply with exactly one option." % i),
            "criteria": criteria,
        }
        for i in range(len(items))
    }
    resp = jev(state, questions)
    out = {}
    for qid, ans in resp["answers"].items():
        idx = int(qid[len(key_prefix):])
        out[items[idx]] = (ans["choice"], round(ans["confidence"], 2))
    return out


def walk_schedule_b(committee_id, cycle, max_pages, per_page, progress_cb):
    """Cursor-walk Schedule B top-by-amount. Returns distinct records."""
    recs, seen = [], set()
    params = {"committee_id": committee_id, "cycle": cycle,
              "per_page": per_page, "sort": "-disbursement_amount"}
    for _ in range(max_pages):
        d = fec("/schedules/schedule_b/", params)
        for x in d["results"]:
            if x.get("sub_id") not in seen:
                seen.add(x["sub_id"])
                recs.append(x)
        progress_cb(len(recs))
        li = d["pagination"]["last_indexes"]
        if not li or not li.get("last_index"):
            break
        params = {"committee_id": committee_id, "cycle": cycle,
                  "per_page": per_page, "sort": "-disbursement_amount",
                  "last_disbursement_amount": li.get("last_disbursement_amount", ""),
                  "last_index": li["last_index"]}
        time.sleep(0.5)
    return recs


def sample_schedule_a(committee_id, cycle, n=100):
    d = fec("/schedules/schedule_a/",
            {"committee_id": committee_id, "cycle": cycle, "per_page": n,
             "is_individual": "true", "sort": "contribution_receipt_amount"})
    return d["results"]


def analyze_side(committee_id, label, cycle, max_pages, progress_cb):
    totals_d = fec("/committee/%s/totals/" % committee_id, {"cycle": cycle})
    totals = totals_d["results"][0] if totals_d["results"] else {}
    progress_cb("totals", 0)

    recs = walk_schedule_b(committee_id, cycle, max_pages, 100,
                           lambda n: progress_cb("walking", n))
    year = str(cycle)
    recs_y = [x for x in recs
              if (x.get("disbursement_date") or "").startswith(year)]

    descs = sorted(set((x.get("disbursement_description") or "UNKNOWN")
                       for x in recs_y))
    uncached = [t for t in descs if t not in TACTIC_CACHE]
    new_maps = {}
    if uncached:
        progress_cb("jev-tactics", len(uncached))
        new_maps = jev_classify(uncached, TACTIC_CRITERIA, "s")
        for t, (choice, conf) in new_maps.items():
            TACTIC_CACHE[t] = {"tactic": choice, "conf": conf, "src": "jev-web"}
        save_cache("tactic_cache.json", TACTIC_CACHE)

    spend, counts = {}, {}
    for x in recs_y:
        t = (x.get("disbursement_description") or "UNKNOWN")
        tactic = TACTIC_CACHE[t]["tactic"]
        spend[tactic] = spend.get(tactic, 0) + (x.get("disbursement_amount") or 0)
        counts[tactic] = counts.get(tactic, 0) + 1

    donors = sample_schedule_a(committee_id, cycle)
    progress_cb("donors", len(donors))
    occs = []
    for x in donors:
        occ = (x.get("contributor_occupation") or "").strip() or None
        occs.append(occ or "UNKNOWN-missing")
    uniq_occs = sorted(set(occs))
    uncached_o = [o for o in uniq_occs if o not in SECTOR_CACHE]
    new_sectors = {}
    if uncached_o:
        progress_cb("jev-sectors", len(uncached_o))
        res = jev_classify(uncached_o, SECTOR_CRITERIA, "o")
        for o, (choice, conf) in res.items():
            SECTOR_CACHE[o] = {"sector": choice, "conf": conf, "src": "jev-web"}
            new_sectors[o] = {"sector": choice, "conf": conf}
        save_cache("sector_cache.json", SECTOR_CACHE)
    donor_mix = {}
    for o in occs:
        s = SECTOR_CACHE[o]["sector"]
        donor_mix[s] = donor_mix.get(s, 0) + 1

    spend_total = sum(spend.values())
    cycle_disb = totals.get("disbursements") or 0
    return {
        "label": label,
        "committee_id": committee_id,
        "cycle": cycle,
        "totals": {
            "receipts": totals.get("receipts"),
            "disbursements": totals.get("disbursements"),
            "individual_contributions": totals.get("individual_contributions"),
            "cash_on_hand_end_period": totals.get("cash_on_hand_end_period"),
        },
        "records_walked": len(recs),
        "records_in_year": len(recs_y),
        "spend_total": round(spend_total, 2),
        "spend_by_tactic": {k: round(v, 2) for k, v in spend.items()},
        "count_by_tactic": counts,
        "coverage": (round(spend_total / cycle_disb, 4) if cycle_disb else None),
        "donor_n": len(donors),
        "donor_by_sector": donor_mix,
        "new_tactic_mappings": {k: {"tactic": v[0], "conf": v[1]}
                                for k, v in new_maps.items()},
        "new_sector_mappings": new_sectors,
    }


def walk_schedule_e(candidate_id, cycle, max_pages, per_page, progress_cb):
    """Cursor-walk Schedule E (independent expenditures) for a candidate."""
    recs, seen = [], set()
    params = {"candidate_id": candidate_id, "cycle": cycle,
              "per_page": per_page, "sort": "-expenditure_amount"}
    for _ in range(max_pages):
        d = fec("/schedules/schedule_e/", params)
        for x in d["results"]:
            if x.get("sub_id") not in seen:
                seen.add(x["sub_id"])
                recs.append(x)
        progress_cb(len(recs))
        li = d["pagination"]["last_indexes"]
        if not li or not li.get("last_index"):
            break
        params = {"candidate_id": candidate_id, "cycle": cycle,
                  "per_page": per_page, "sort": "-expenditure_amount"}
        for k, v in li.items():
            params[k] = v
        time.sleep(0.5)
    return recs


def committee_display_name(cid):
    if cid in NAMES_CACHE:
        return NAMES_CACHE[cid]
    try:
        d = fec("/committee/%s/" % cid, {})
        name = (d["results"][0].get("name") if d["results"] else None) or cid
    except Exception:
        name = cid
    NAMES_CACHE[cid] = name
    save_cache("committee_names.json", NAMES_CACHE)
    return name


TOP_SPENDERS = 14


def build_sankey(a_cand, a_label, b_cand, b_label, cycle, max_pages,
                 progress_cb):
    """Spender committee -> Jev tactic -> candidate outcome (Schedule E)."""
    sides = [("A", a_cand, a_label), ("B", b_cand, b_label)]
    all_recs = []
    for side, cand, _ in sides:
        recs = walk_schedule_e(cand, cycle, max_pages, 100,
                               lambda n, s=side: progress_cb("walk-" + s, n))
        for x in recs:
            x["_side"] = side
        all_recs += recs
    year = str(cycle)
    recs_y = []
    seen_lines = set()
    for x in all_recs:
        if not (x.get("expenditure_date") or "").startswith(year):
            continue
        if (x.get("expenditure_amount") or 0) <= 0:
            continue
        if x.get("filing_form") == "F24":
            continue  # 24/48hr notice; FEC aggregates exclude these (double count)
        line_key = (x.get("committee_id"), x.get("expenditure_amount"),
                    x.get("expenditure_date"), x.get("expenditure_description"),
                    x.get("candidate_id"), x.get("support_oppose_indicator"))
        if line_key in seen_lines:
            continue  # some filers repeat the program total on every payee line
        seen_lines.add(line_key)
        recs_y.append(x)

    descs = sorted(set((x.get("expenditure_description") or "UNKNOWN")
                       for x in recs_y))
    uncached = [t for t in descs if t not in TACTIC_CACHE]
    new_maps = {}
    if uncached:
        progress_cb("jev", len(uncached))
        new_maps = jev_classify(uncached, TACTIC_CRITERIA, "e")
        for t, (choice, conf) in new_maps.items():
            TACTIC_CACHE[t] = {"tactic": choice, "conf": conf, "src": "jev-web-e"}
        save_cache("tactic_cache.json", TACTIC_CACHE)

    spender_total = {}
    ct, to = {}, {}
    for x in recs_y:
        spender = x.get("committee_id") or "UNKNOWN"
        tactic = TACTIC_CACHE[(x.get("expenditure_description")
                               or "UNKNOWN")]["tactic"]
        so = "S" if (x.get("support_oppose_indicator") or "S") == "S" else "O"
        outcome = (x["_side"], so)
        amt = x.get("expenditure_amount") or 0
        spender_total[spender] = spender_total.get(spender, 0) + amt
        ct[(spender, tactic)] = ct.get((spender, tactic), 0) + amt
        to[(tactic, outcome)] = to.get((tactic, outcome), 0) + amt

    top = sorted(spender_total, key=lambda c: -spender_total[c])[:TOP_SPENDERS]
    top_set = set(top)
    other_n = len(spender_total) - len(top)
    OTHER = "OTHER_COMMITTEES"

    def bucket(spender):
        return spender if spender in top_set else OTHER

    ct2 = {}
    for (spender, tactic), amt in ct.items():
        k = (bucket(spender), tactic)
        ct2[k] = ct2.get(k, 0) + amt

    progress_cb("names", len(top))
    names = {c: committee_display_name(c) for c in top}

    labels = {a_cand: a_label, b_cand: b_label}
    outcome_ids = {}
    for side, cand in (("A", a_cand), ("B", b_cand)):
        for so, verb in (("S", "supported"), ("O", "opposed")):
            oid = "OUT_%s_%s" % (side, so)
            outcome_ids[(side, so)] = oid

    nodes = []
    for c in top:
        nodes.append({"id": "C_" + c, "label": names[c], "kind": "committee"})
    if other_n > 0:
        nodes.append({"id": "C_" + OTHER,
                      "label": "Other committees (%d)" % other_n,
                      "kind": "committee"})
    tactics_used = sorted(set(list(k[1] for k in ct2) +
                              list(k[0] for k in to)))
    for t in tactics_used:
        nodes.append({"id": "T_" + t, "label": t, "kind": "tactic"})
    for (side, so), oid in outcome_ids.items():
        cand = a_cand if side == "A" else b_cand
        verb = "Pro-%s spending" % labels[cand] if so == "S" else "Anti-%s spending" % labels[cand]
        nodes.append({"id": oid, "label": verb,
                      "kind": "outcome-" + so})

    links = []
    for (spender, tactic), amt in ct2.items():
        links.append({"source": "C_" + spender, "target": "T_" + tactic,
                      "value": round(amt, 2)})
    for (tactic, outcome), amt in to.items():
        links.append({"source": "T_" + tactic,
                      "target": outcome_ids[outcome], "value": round(amt, 2)})

    return {
        "nodes": nodes,
        "links": links,
        "records": len(recs_y),
        "total": round(sum(spender_total.values()), 2),
        "new_mappings": len(new_maps),
    }


def run_job(job_id, payload):
    job = JOBS[job_id]
    try:
        cycle = payload["cycle"]
        max_pages = int(payload.get("max_pages", 10))

        def cb_factory(side):
            def cb(stage, n):
                job["progress"] = {"side": side, "stage": stage, "n": n}
            return cb

        a = analyze_side(payload["a_committee"], payload.get("a_label", "A"),
                         cycle, max_pages, cb_factory("A"))
        job["progress"] = {"side": "B", "stage": "starting", "n": 0}
        b = analyze_side(payload["b_committee"], payload.get("b_label", "B"),
                         cycle, max_pages, cb_factory("B"))
        result = {"a": a, "b": b, "cycle": cycle,
                  "tactic_cache_size": len(TACTIC_CACHE),
                  "sector_cache_size": len(SECTOR_CACHE)}
        if payload.get("a_candidate") and payload.get("b_candidate"):
            job["progress"] = {"side": "IE", "stage": "starting", "n": 0}

            def ie_cb(stage, n):
                job["progress"] = {"side": "IE", "stage": stage, "n": n}

            result["sankey"] = build_sankey(
                payload["a_candidate"], payload.get("a_label", "A"),
                payload["b_candidate"], payload.get("b_label", "B"),
                cycle, min(max_pages, 8), ie_cb)
        job["status"] = "done"
        job["result"] = result
    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e) + "\n" + traceback.format_exc(limit=5)


class Handler(BaseHTTPRequestHandler):
    server_version = "FECJev/1.0"

    def log_message(self, *args):
        pass

    def send_json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path, qs = parsed.path, urllib.parse.parse_qs(parsed.query)
        try:
            if path == "/" or path == "/index.html":
                with open(os.path.join(HERE, "index.html"), "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif path == "/api/presets":
                self.send_json(PRESETS)
            elif path == "/api/search/candidates":
                q = qs.get("q", [""])[0]
                d = fec("/candidates/search/",
                        {"q": q, "per_page": 10})
                self.send_json([{
                    "candidate_id": r["candidate_id"], "name": r["name"],
                    "office": r.get("office_full"), "party": r.get("party_full"),
                    "state": r.get("state"),
                    "election_years": r.get("election_years"),
                } for r in d["results"]])
            elif path.startswith("/api/candidate/") and path.endswith("/committees"):
                cid = path.split("/")[3]
                cycle = qs.get("cycle", ["2024"])[0]
                d = fec("/committees/", {"candidate_id": cid, "cycle": cycle,
                                         "per_page": 20})
                self.send_json([{
                    "committee_id": r["committee_id"], "name": r["name"],
                    "designation": r.get("designation_full"),
                    "type": r.get("committee_type_full"),
                } for r in d["results"]])
            elif path.startswith("/api/committee/"):
                cid = path.split("/")[3]
                cycle = qs.get("cycle", ["2024"])[0]
                info = fec("/committee/%s/" % cid, {})
                totals = fec("/committee/%s/totals/" % cid, {"cycle": cycle})
                self.send_json({
                    "info": info["results"][0] if info["results"] else {},
                    "totals": totals["results"][0] if totals["results"] else {},
                })
            elif path.startswith("/api/jobs/"):
                job_id = path.split("/")[3]
                job = JOBS.get(job_id)
                if not job:
                    self.send_json({"error": "unknown job"}, 404)
                else:
                    self.send_json(job)
            else:
                self.send_json({"error": "not found"}, 404)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
            if parsed.path == "/api/analyze":
                for k in ("a_committee", "b_committee", "cycle"):
                    if k not in payload:
                        self.send_json({"error": "missing " + k}, 400)
                        return
                job_id = "job-%d" % (int(time.time() * 1000) % 1000000)
                JOBS[job_id] = {"status": "running",
                                "progress": {"side": "A", "stage": "starting",
                                             "n": 0}}
                t = threading.Thread(target=run_job, args=(job_id, payload),
                                     daemon=True)
                t.start()
                self.send_json({"job_id": job_id})
            else:
                self.send_json({"error": "not found"}, 404)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print("FEC x Jev on http://127.0.0.1:%d" % PORT, flush=True)
    srv.serve_forever()
