import pooler
from report.interface import report_int
from report_tools import pdf_fill,pdf_merge,html2pdf
from datetime import datetime
from mako.template import Template

def name_rank(emp,incl_dept=False):
    str=emp.full_name
    if emp.rank:
        str+=", "+emp.rank
    if emp.subrank:
        str+=", "+emp.subrank
    if emp.title:
        str+=", "+emp.title
    if incl_dept and emp.department_id.long_name:
        str+=", "+emp.department_id.long_name
    return str

def role_emp(cr,uid,role_name):
    pool=pooler.get_pool(cr.dbname)
    res=pool.get("wkf.role").search(cr,uid,[("name","ilike",role_name)])
    if not res:
        return None
    role_id=res[0]
    emp_id=pool.get("wkf.role").find_employee(cr,uid,[role_id])
    if not emp_id:
        return None
    emp=pool.get("employee").browse(cr,uid,emp_id)
    return emp

def choice_date(cr,uid,decision,choice,role,tdy_id):
    pool=pooler.get_pool(cr.dbname)
    res=pool.get("wkf.hist").search(cr,uid,[("decision_id.name","ilike",decision),("choice_id.name","ilike",choice),("decider_id.role_id.name","ilike",role),("tdy_id","=",tdy_id)])
    if not res:
        return ""
    hist=pool.get("wkf.hist").browse(cr,uid,res[0])
    return str(hist.date)[:10]

def fmt_fields(cr,uid,tdy,lang=None):
    print "fmt_fields"
    vals={}

    emp=tdy.requester_id
    str=emp.title or ""
    if emp.rank:
        str+=", "+emp.rank
    else:
        if emp.position_series:
            str+=", "+emp.position_series
        if emp.grade:
            str+=", Grade "+emp.grade
    vals["position"]=str

    vals["num_days"]=tdy.tdy_days
    vals["first_day"]=fmt_date(tdy.dep_date)
    vals["itin"]=tdy.itin

    projects={}
    for proj in tdy.projects:
        k=proj.project_id.name,proj.site_id
        projects[k]=projects.setdefault(k,0.0)+proj.percent
    top_projs=sorted([(amt,k) for k,amt in projects.items()])[:3]
    str=", ".join(["%s / %s"%(proj,site) for a,(proj,site) in top_projs])
    apcs={}
    for apc in tdy.apcs:
        k=(apc.apc_id.code or apc.apc_id.name)+"-"+apc.apc_id.category_id.name
        apcs[k]=apcs.setdefault(k,0.0)+apc.amount
    print "apcs",apcs
    str+="\n"
    str+=", ".join(["%s %s by %s"%(lang.format("%.2f",amt,grouping=True,monetary=True),"USD",apc) for apc,amt in apcs.items()])
    vals["funding"]=str

    str=""
    if tdy.loa:
        str+="\n"+tdy.loa
    vals["loa"]=str

    emp=tdy.req_official_id
    if emp:
        vals["request_official"]=name_rank(emp,incl_dept=True)

    emp=tdy.app_official_id
    if emp:
        vals["approve_official"]=name_rank(emp)

    emp=tdy.auth_official_id
    if emp:
        vals["authorize_official"]=name_rank(emp)

    str=""
    if tdy.purpose.find("\n")!=-1 or len(tdy.purpose)>30:
        str+="Purpose of travel: "+tdy.purpose+"\n"
    if tdy.notes:
        str+="\n"+tdy.notes
    vals["remarks"]=str

    pool=pooler.get_pool(cr.dbname)
    m=[]
    for mode in tdy.travel_modes:
        m.append("%s%s"%(mode.categ1,mode.categ2))
    vals["modes"]=m

    amend=False
    for am in tdy.amendments:
        if am.state=="done":
            amend=True
            break
    if amend:
        vals["auth_type"]="TDY-Amendment"
    else:
        vals["auth_type"]="TDY"

    print "vals",vals
    return vals

def fmt_amount(amt,lang):
    if not amt:
        return "0"
    return lang.format("%.2f",amt,grouping=True,monetary=True)

def fmt_date(date):
    res=date[:4]+date[5:7]+date[8:10]
    print "fmt_date",date,"->",res
    return res

class report(report_int):
    def create(self,cr,uid,ids,data,context={}):
        pool=pooler.get_pool(cr.dbname)
        tdy=pool.get("tdy.request").browse(cr,uid,ids[0])
        lang_id=pool.get("res.lang").search(cr,uid,[("code","=","en_US")])[0]
        lang=pool.get("res.lang").browse(cr,uid,lang_id)
        fields=fmt_fields(cr,uid,tdy,lang=lang)
        vals={
            "field1":fmt_date(tdy.date),
            "field2":tdy.requester_id.lname+", "+tdy.requester_id.fname,
            "field3":tdy.ssn or "",
            "field4":fields.get("position") or "",
            "field5":"USAMC-AFRIMS, BANGKOK, THAILAND",
            "field6":"USAMC-AFRIMS, APO AP 96546 (W2DRAA)",
            "field7":"02-696-2752",
            "field8": fields.get("auth_type") or "",
            "field9": tdy.purpose.find("\n")==-1 and len(tdy.purpose)<=30 and tdy.purpose or "See item 16. Remarks",
            "field10a":fields.get("num_days") or "",
            "field10b":fields.get("first_day") or "",
            "field11":fields.get("itin") or "",
            "field11v": "", #"field11v": "X",
            "field13b_check": tdy.other_rate and "X" or "",
            "field13b": tdy.other_rate and "%.0f Baht/day"%tdy.other_rate or "",
            "field14a": fmt_amount(tdy.cost_per_diem_man or tdy.cost_per_diem,lang),
            "field14b": fmt_amount(tdy.cost_travel_man or tdy.cost_travel,lang),
            "field14c": fmt_amount(tdy.cost_other+tdy.cost_regis,lang),
            "field14d": fmt_amount(tdy.cost_total,lang),
            "field15": fmt_amount(tdy.advance_amount,lang),
            "field16": fields.get("remarks") or "",
            "field17": fields.get("request_official") or "",
            "field18": fields.get("approve_official") or "",
            "field19": fields.get("funding") or "",
            "field19b": fields.get("loa") or "",
            "field20": fields.get("authorize_official") or "",
            "field21": fmt_date(tdy.date),
            "field22": (tdy.po_no or "")+"   "+(tdy.doc_no or ""),
            "field16cont":"",
            "f12ar": "CR" in fields["modes"] and "X" or "",
            "f12aa": "CA" in fields["modes"] and "X" or "",
            "f12ab": "CB" in fields["modes"] and "X" or "",
            "f12as": "CS" in fields["modes"] and "X" or "",
            "f12ba": "GA" in fields["modes"] and "X" or "",
            "f12bv": "GV" in fields["modes"] and "X" or "",
            "f12bs": "GS" in fields["modes"] and "X" or "",
            "f12cc": "LC" in fields["modes"] and "X" or "",
            "f12ct": "LT" in fields["modes"] and "X" or "",
            "f12co": "LO" in fields["modes"] and "X" or "",
        }
        pdf=pdf_fill("addons/ac_afrims/report/pdf/form_1610.pdf",vals)
        return (pdf,"pdf")
report("report.form.1610")

class report(report_int):
    def create(self,cr,uid,ids,data,context={}):
        tmpl=Template("""
<html>
<style>
th {
    padding: 5px;
}
td {
    padding: 5px;
}
</style>
<body style="font-size:12px">
<h1 style="text-align:center;font-size:20px">TDY Request Memo</h1>

<b>Date</b>: ${tdy.date}<br/>
<b>Running No</b>: ${tdy.name}<br/>
<b>Requester</b>: ${tdy.requester_id.full_name}<br/>
<b>Department</b>: ${tdy.department_id.long_name}<br/>
<b>Section</b>: ${tdy.section_id.name}<br/>
<b>Category</b>: ${tdy.type}<br/>
<b>Document No</b>: ${tdy.doc_no or ""}<br/>
<b>Purpose</b>: ${tdy.purpose.replace("\\n","<br/>")}<br/>
<b>Itinerary</b>:<br/>
${fields["itin"].replace("\\n","<br/>")}<br/>
<b>Cost estimates</b>:
<ul>
    <li>Per Diem: ${"%.2f"%tdy.cost_per_diem}
    <li>Travel: ${"%.2f"%tdy.cost_travel}
    <li>Other: ${"%.2f"%tdy.cost_other}
    <li>Total: ${"%.2f"%tdy.cost_total}
</ul>
<b>Funding</b>:<br/>
${(fields.get("funding") or "").replace("\\n","<br/>")}<br/>
<b>Remarks</b>:<br/>
${(tdy.notes or "").replace("\\n","<br/>")}
""")
        pool=pooler.get_pool(cr.dbname)
        tdy=pool.get("tdy.request").browse(cr,uid,ids[0])
        lang_id=pool.get("res.lang").search(cr,uid,[("code","=","en_US")])[0]
        lang=pool.get("res.lang").browse(cr,uid,lang_id)
        fields=fmt_fields(cr,uid,tdy,lang=lang)
        html=tmpl.render(tdy=tdy,fields=fields)
        print "HTML:"
        print html
        pdf=html2pdf(html)
        return (pdf,"pdf")
report("report.tdy.memo")
