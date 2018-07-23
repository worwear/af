import pooler
from report.interface import report_int
from report_tools import pdf_fill,pdf_merge,html2pdf
from mako.template import Template
import datetime
import math
from pprint import pprint as pp

def name_rank(emp):
    str=emp.full_name
    if emp.rank:
        str+=", "+emp.rank
        if emp.subrank:
            str+=", "+emp.subrank
    elif emp.title:
        str+=", "+emp.title
    return str

def name_default(emp):
    str=emp.full_name
    if emp.rank:
        str+="\n"+emp.rank
        if emp.subrank:
            str+=", "+emp.subrank
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

def choice_date(cr,uid,decision,choice,role,pr_id):
    pool=pooler.get_pool(cr.dbname)
    res=pool.get("wkf.hist").search(cr,uid,[("decision_id.name","ilike",decision),("choice_id.name","ilike",choice),("decider_id.role_id.name","ilike",role),("pr_id","=",pr_id)])
    if not res:
        return ""
    hist=pool.get("wkf.hist").browse(cr,uid,res[0])
    return str(hist.date)[:10]

def choice_sign(cr,uid,decision,choice,role,pr_id):
    pool=pooler.get_pool(cr.dbname)
    res=pool.get("wkf.hist").search(cr,uid,[("decision_id.name","ilike",decision),("choice_id.name","ilike",choice),("decider_id.role_id.name","ilike",role),("pr_id","=",pr_id)])
    if not res:
        return ""
    hist=pool.get("wkf.hist").browse(cr,uid,res[0])
    return hist.signature or ""

def fmt_fields(cr,uid,pr,lang=None):
    pool=pooler.get_pool(cr.dbname)
    #print "fmt_fields"
    vals={}
    s=""
    if pr.purpose:
        s+=pr.purpose+"\n"
    for line in pr.lines:
        if line.purpose:
            s+="Item %d: %s\n"%(line.sequence,line.purpose)
    vals["purpose"]=s

    dept=pr.department_id
    s=dept.long_name
    if dept.address1:
        s+=", "+dept.address1
    if dept.address2:
        s+=", "+dept.address2
    s+="\nUSAMC-AFRIMS"
    #vals["from"]=s
    vals["from"]=" Department of Virology\n USAMD-AFRIMS\n APO AP 96546 " # directly use

    s=dept.long_name
    if dept.address1:
        s+=", "+dept.address1
    #vals["deliver_to"]=s
    vals["deliver_to"]=" Department of Logistics\n Supply Office, 315/6 Rajvithi Road, Rajthevee, BKK 10400 " #directly use

    s=""
    if pr.supplier_id:
        s+=pr.supplier_id.name
        if pr.supplier_id.address:
            addr=pr.supplier_id.address[0]
            s+="\n"+(addr.street or "")
            #if addr.seet2:
            #    s+="\n"+addr.seet2
            s+="\n"
            if addr.city:
                s+=addr.city
            if addr.zip:
                s+=","+addr.zip
            if addr.state_id:
                s+=","+addr.state_id
            if addr.country_id:
                s+=","+addr.country_id.name
            if addr.name:
                s+="\n"
                s+="POC: "+addr.name
            if addr.phone or addr.fax:
                s+="\n"
                if addr.phone:
                    s+="Phone: "+addr.phone
                if addr.fax:
                    s+=", Fax: "+addr.fax
    vals["supplier"]=s

    projects={}
    for line in pr.lines:
        for proj in line.projects:
            k=proj.project_id.name,proj.site_id
            projects[k]=projects.setdefault(k,0.0)+line.subtotal*proj.percent/100.0
    top_projs=sorted([(amt,k) for k,amt in projects.items()])[:3]

    s=", ".join(["%s / %s"%(proj,site) for a,(proj,site) in top_projs])
    total = 0.0
    apcs={}
    for apc in pr.apcs:
        k=k and apc.apc_id.code or apc.apc_id.name
        apcs[k]=apcs.setdefault(k,0.0)+apc.amount
        total += apc.amount

    s+="\n Total: %s %s" % ( lang.format("%.2f",total,grouping=True,monetary=True),pr.currency_id.code )
    s+="\n WBS: %s" % ','.join(apcs.keys())

    vals["funding"]=s #TODO

    emp=pr.init_officer_id
    if emp:
        vals["dept_chief"]=name_rank(emp)
        vals["dept_chief_date"]=choice_date(cr,uid,"Department chief approval","Approve","Department Chief",pr.id)
        vals["dept_chief_phone"]=emp.dl or ''
        vals["dept_chief_sign"]=choice_sign(cr,uid,"Department chief approval","Approve","Department Chief",pr.id)

    emp=pr.supply_officer_id
    if emp:
        vals["logis_chief"]=name_rank(emp)
        #vals["logis_chief"]="%s %s" % ( emp.fname,emp.lname)
        vals["logis_chief_date"]=choice_date(cr,uid,"Logistics chief approval","Approve","Logistics Chief",pr.id)
        vals["logis_chief_sign"]=choice_sign(cr,uid,"Logistics chief approval","Approve","Logistics Chief",pr.id)

    emp=pr.cert_officer_id
    if emp:
        vals["budget_chief"]=name_rank(emp)
        vals["budget_chief_date"]=choice_date(cr,uid,"Budget approval","Approve","Budget Chief",pr.id)
        vals["budget_chief_sign"]=choice_sign(cr,uid,"Budget approval","Approve","Budget Chief",pr.id)

    d0=datetime.datetime.strptime(pr.date,"%Y-%m-%d")
    vals["date"]= "%s %s" % ( int(d0.strftime("%d")),  d0.strftime("%B %Y") )
    d1=d0+datetime.timedelta(days=30)

    res= pool.get('employee').search(cr,uid,[('id','=',pr.requester_id.id)])
    if not res:
        s=''
    else:
        emp = pool.get('employee').browse(cr,uid,res[0])
        l = pr.purch_admin_id.lname
        s = pr.purch_admin_id.fname +" "+ l[0] +" ("+ pr.purch_admin_id.email +") \n" + emp.email 
        #s += "\n%s" % (emp.email)
    vals['field10'] = s

    #vals["no_later"]=d1.strftime("%d %b %Y")
    vals["no_later"]="%s %s" % ( int(d1.strftime("%d")),  d1.strftime("%B %Y") )
    #res= pool.get('employee').search(cr,uid,[('title','like','Billing Official')])
    res= pool.get('employee').search(cr,uid,[('employee_no','=','31')])
    if not res:
        s=''
    else:
        emp = pool.get('employee').browse(cr,uid,res[0])
        s = name_rank(emp).upper()
        s += ", %s" % (emp.title)
    vals['field31'] = s

    #res= pool.get('employee').search(cr,uid,[('title','like','Chief, Logistics')])
    res= pool.get('employee').search(cr,uid,[('employee_no','=','34')])
    if not res:
        s=''
    else:
        emp = pool.get('employee').browse(cr,uid,res[0])
        s = name_default(emp).upper()
        s += "\n%s" % (emp.title)
    vals['field34'] = s

    #print "vals",vals
    return vals

def get_newline(word,size=25):
    if len(word)<size:
        return "\n"
    import math
    return "\n"*int(math.ceil(len(word)/float(size)))

class report(report_int):
    def create(self,cr,uid,ids,data,context={}):
        limit=4#pr_lines limit in reports
        pool=pooler.get_pool(cr.dbname)
        vals={}
        lang_id=pool.get("res.lang").search(cr,uid,[("code","=","en_US")])[0]
        lang=pool.get("res.lang").browse(cr,uid,lang_id)
        pr=pool.get("purchase.request").browse(cr,uid,ids[0])
        fields=fmt_fields(cr,uid,pr,lang=lang)
        cont_lines=len(pr.lines)>=limit
        cont_purpose=fields["purpose"].count("\n")>3
        need_cont=cont_lines or cont_purpose
        num_pg=need_cont and 2 or 1
        vals={
            "field1": "WT0J3Y",
            "field1b":pr.name,
            "field2": pr.doc_no or "",
            "field3": fields["date"],
            #"field4": "PURCHASING AND CONTRACTING OFFICER, USAMC-AFRIMS",
            "field4": "Purchasing & Contracting Officer\n US Embassy Thailand (GSO)\n APO AP 96546",
            #"field5": "CHIEF, DEPARTMENT OF LOGISTICS, USAMC-AFRIMS",
            "field5": "Department of Logistics Procurement \n USAMD-AFRIMS \n APO AP 96546",
            "field6": fields["from"],
            #"field7": "USAMC-AFRIMS APO AP 96546",
            "field7": "Department of Virology\n USAMD-AFRIMS, APO AP 96546",
            "field8": fields["deliver_to"],
            "field9": fields["no_later"],
            "field10": fields["field10"],
            #"field11": pr.purch_admin_id.dl or "",
            "field11": pr.purch_admin_id.dl +" #"+pr.purch_admin_id.phone_ext or "",
            "field12": "X",
            "field12_1": "AR 710-2",
            "field25": not cont_purpose and fields["purpose"] or "**See continuation sheet**",
            "field14": "",
            "field15": "",
            "field15h": pr.description or "",
            "field18ah": pr.lines[0].currency_id.name,
            "field18bh": pr.lines[0].currency_id.name,
            #"field15b": "Suggested supplier:\n"+fields["supplier"],#TODO:Fix this
            "field16": "",
            "field17": "",
            "field19": fields["funding"],
            "field18a": "",
            "field18b": "",
            "field27": fields["dept_chief"].upper(),
            "field29": fields["dept_chief_date"],
            "field30": fields["dept_chief_phone"],
            "field28": fields["dept_chief_sign"],
            #"field20": fields["budget_chief"],
            "field20": "Chadchadaporn P.\n Budget Analyst, FSN-9",
            "field22": fields["budget_chief_date"],
            "field21": fields["budget_chief_sign"],
            #"field31": fields["logis_chief"].upper(),
            "field31": fields["field31"],
            "field33": fields["logis_chief_date"],
            "field32": fields["logis_chief_sign"],
            "field34": fields["field34"],
            "pa": 1,
            "po": num_pg,
        }
        for line in pr.lines[:limit]:
            newline=get_newline(line.product_id and line.product_id.name_get()[0][1] or line.name,35)

            vals["field14"]+="%d"%line.sequence+newline
            vals["fiels15"]=""
            vals["field16"]+="%.2f"%line.qty+newline
            vals["field17"]+="%s"%line.uom_id.name+newline
            #vals["field18ah"]+= pr.currency_id.name,
            vals["field18a"]+="%s"%lang.format("%.2f",line.price_unit,grouping=True)+newline
            vals["field18b"]+="%s"%lang.format("%.2f",line.subtotal,grouping=True)+newline
            if (line.product_id):
                vals["field15"]+="%s"%(line.product_id.name_get()[0][1])+"\n"
            else:
                vals["field15"]+="%s"%(line.name)+"\n"
        if len(pr.lines) < limit:
            #vals["field15"]+="**See continuation sheet**\n"
            vals["field15"]+= "\nSuggested Supplier\n"+fields['supplier']+"\n\n"

        # because of some problem in PDF fields in IE...
        vals["field8n"]=vals["field8"]
        vals["field11n"]=vals["field11"]
        vals["field15n"]=vals["field15"]
        vals["field16n"]=vals["field16"]
        vals["field30n"]=vals["field30"]

        from pprint import pprint
        pprint(vals)

        pdf=pdf_fill("addons/ac_afrims/report/pdf/form_3953.pdf",vals)
        if not need_cont:
            return (pdf,"pdf")
        vals={
            "line_item": "",
            "line_supplies": "",
            "line_quantity": "",
            "line_unit": "",
            "line_unit_price": "",
            "line_amount": "",
        }
        if cont_lines:
            # suggested section
            line_suggested= "Suggested Supplier\n"+fields['supplier']+"\n\n"
            vals["line_supplies"]+=line_suggested
            line_start="\n"*line_suggested.count('\n')
            vals["line_item"]+=line_start
            vals["line_quantity"]+=line_start
            vals["line_unit"]+=line_start
            vals["line_unit_price"]+=line_start
            vals["line_amount"]+=line_start
            #line loop
            for line in pr.lines[limit:]:
                newline=get_newline(line.product_id and line.product_id.name_get()[0][1] or line.name,65)

                vals["line_item"]+="%d"%line.sequence+newline
                vals["line_supplies"]+="%s\n"%(line.product_id and line.product_id.name_get()[0][1] or line.name)
                vals["line_quantity"]+="%.2f"%line.qty+newline
                vals["line_unit"]+="%s"%line.uom_id.name+newline
                vals["line_unit_price"]+="%s"%lang.format("%.2f",line.price_unit,grouping=True)+newline
                vals["line_amount"]+="%s"%lang.format("%.2f",line.subtotal,grouping=True)+newline

            if cont_purpose:
                vals["line_supplies"]+"\n"
        if cont_purpose:
            vals["line_supplies"]+="Purpose:\n"+fields["purpose"]
        pdf_cont=pdf_fill("addons/ac_afrims/report/pdf/form_336.pdf",vals)
        pdf_all=pdf_merge(pdf,pdf_cont)
        return (pdf_all,"pdf")
report("report.form.3953")

def top_projects(line):
    amounts={}
    for proj in line.projects:
        k=proj.project_id.name,proj.site_id
        amounts[k]=amounts.setdefault(k,0.0)+line.subtotal*proj.percent/100.0
    res=sorted([(a,k) for k,a in amounts.items()])
    return ", ".join("%s / %s"%(proj,site) for a,(proj,site) in res[:1])

class report_3161(report_int):
    def create(self,cr,uid,ids,data,context={}):
        pool=pooler.get_pool(cr.dbname)
        lang_id=pool.get("res.lang").search(cr,uid,[("code","=","en_US")])[0]
        lang=pool.get("res.lang").browse(cr,uid,lang_id)
        pr=pool.get("purchase.request").browse(cr,uid,ids[0])
        records=[]

        line_per_page=12
        start=0
        total_page=int(math.ceil(len(pr.lines)/12.0))

        for page in range(total_page):
            vals={
                "issue": "X",
                "field1": pr.doc_no or "",
                "field3": "Department of Logistics, USAMC-AFRIMS, Supply Room Officer, Attn: Khun Supoj",
                "field4": "",
                "field8": "%s, %s"%(pr.department_id.long_name or "",pr.requester_id.full_name),
                "field13d": pr.date,
                "field9": pr.name,
                "field13by": pr.purch_admin_id.full_name,
            }

            vals['page_no']=page+1
            i=0
            for line in pr.lines[start:start+line_per_page]:
                i+=1
                vals.update({
                    "fa%d"%i: line.sequence,
                    "fb%d"%i: line.product_id and line.product_id.default_code or "",
                    "fc%d"%i: line.product_id and line.product_id.name or line.name,#XXX
                    "fd%d"%i: line.uom_id.name,
                    "fe%d"%i: "%.2f"%line.qty,
                    "fjb%d"%i: top_projects(line),
                    "fjd%d"%i: line.notes or '',  #pass, #weng edit
                })
            if int(page)==int(total_page)-1:
                vals["fc%d"%(i+1)]="*** Nothing Follows ***"
            start+=line_per_page
            records.append(vals)

        pdf_all=''
        for r in records:
            if not pdf_all:
                pdf_all = pdf_fill("addons/ac_afrims/report/pdf/form_3161.pdf",r)
            else:
                pdf_all = pdf_merge(pdf_all,pdf_fill("addons/ac_afrims/report/pdf/form_3161.pdf",r))

        return (pdf_all,"pdf")
report_3161("report.form.3161")

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
<h1 style="text-align:center;font-size:20px">Purchase Request Memo</h1>

<b>Date</b>: ${pr.date}<br/>
<b>Running No</b>: ${pr.name}<br/>
<b>PR Type</b>: ${pr.type}<br/>
<b>Requester</b>: ${pr.requester_id.full_name}<br/>
<b>Department</b>: ${pr.department_id.long_name}<br/>
<b>Section</b>: ${pr.section_id.name}<br/>
<b>Currency</b>: ${pr.currency_id.name}<br/>
<b>Suggested supplier</b>: ${fields.get("supplier","").replace("\\n","<br/>")}<br/>
<b>Document No</b>: ${pr.doc_no or ""}<br/>
<b>Description</b>: ${(pr.description or "").replace("\\n","<br/>")}<br/>
<b>Purpose</b>: ${pr.purpose.replace("\\n","<br/>")}<br/>
<br/>
<table border="0.5">
<tr>
<th width="5%">No.</th>
<th width="50%">Description</th>
<th>Qty</th>
<th>UoM</th>
<th>Unit Price</th>
<th>Subtotal</th>
</tr>
% for line in pr.lines:
<tr>
<td>${line.sequence}</td>
<td>${line.name}</td>
<td>${line.qty}</td>
<td>${line.uom_id.name}</td>
<td>${line.price_unit}</td>
<td>${line.subtotal}</td>
</tr>
% endfor
</table>

<br/>
<b>Funding</b>:<br/>
${(fields.get("funding") or "").replace("\\n","<br/>")}<br/>
<b>Remarks</b>:<br/>
${(pr.notes or "").replace("\\n","<br/>")}
</body>
</html>""")
        pool=pooler.get_pool(cr.dbname)
        pr=pool.get("purchase.request").browse(cr,uid,ids[0])
        lang_id=pool.get("res.lang").search(cr,uid,[("code","=","en_US")])[0]
        lang=pool.get("res.lang").browse(cr,uid,lang_id)
        fields=fmt_fields(cr,uid,pr,lang=lang)
        html=tmpl.render(pr=pr,fields=fields)
        #print "HTML:"
        #print html
        pdf=html2pdf(html)
        return (pdf,"pdf")
report("report.pr.memo")
