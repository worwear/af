##############################################################################
#
#    Copyright (C) 2009-2010 Almacom (Thailand) Ltd.
#    http://almacom.co.th/
#
##############################################################################

from osv import osv,fields
import time
import re
import datetime
import tools
import urllib2
import zipfile
import cStringIO as StringIO
import csv
import base64
from pprint import pprint

################################
### UTILS ######################
################################

def get_user_defaults(self,cr,uid,field,value):
    #print "get_user_defaults",field,value
    res=self.pool.get("ir.values").get(cr,uid,"default","%s=%s"%(field,value),[self._name])
    vals={}
    for id,field,value in res:
        vals[str(field)]=value
    #print "vals",vals
    return vals

def fmt_loa(s):
    lines=s.split("\n")
    group={}
    for line in lines:
        res=re.match("(.*)\((.+)\)(.*)",line)
        if not res:
            continue
        group.setdefault((res.group(1),res.group(3)),[]).append(res.group(2))
    s2=""
    for (left,right),eors in sorted(group.items()):
        s2+="%s(%s)%s\n"%(left," / ".join(eors),right)
    return s2

################################
### BUDGET #####################
################################

class approved_budget_summary(osv.osv):
    _name="approved.budget.summary"


    def calculater_m(self,cr,uid,ids,name,arg,context={}):
        vals={}
        for bud in self.browse(cr,uid,ids):
            amt =0.0
            amt = (bud.fte*12)/100
            vals[bud.id] = amt
        return vals

    _columns={
        "category": fields.char("Category",size=64,select=1),
        "name": fields.char("Item Description",size=64,select=1),
        "funding_id": fields.char("Funding",size=64,select=1),
        "project_id": fields.char("Project Name",size=64,select=1),
        "fte": fields.float("FTE(%)",size=64,select=1),
        "calculated_month": fields.function(calculater_m,method=True,type="float",string="Calculate month"),
        "period_start": fields.date("Period Start",select=1),
        "period_end": fields.date("Period End",select=1),
        "usd_text": fields.float("Usd",size=64,select=1),
        "remark1": fields.text("Remark I",select=1),
        "remark2": fields.text("Remark II",select=1),
    }

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        period_start = ''
        period_end = ''
        for i in range(len(args)):
            if args[i][0] == 'period_start':
                period_start = args[i][2]
            if args[i][0] == 'period_end':
                period_end = args[i][2]
        if period_start != '' and period_end != '':
            cr.execute('''select id from approved_budget_summary where (period_start >= '%s' and period_start <= '%s') or (period_end >= '%s' and period_end <= '%s') '''%(period_start,period_end,period_start,period_end) )
            bud_id = map(lambda x:x[0] , cr.fetchall())
            args = []
            args = [('id','in',bud_id)]
        res = super(approved_budget_summary, self).search(cr, uid, args, offset, limit, order, context, count)
        return res
approved_budget_summary()

class budget_summary(osv.osv):
    _name="budget.summary"

    def amount(self,cr,uid,ids,name,arg,context={}):
        vals={}
        for bs in self.browse(cr,uid,ids):
            amt=0.0
            amt_usd=0.0
            amt_other=0.0
            amt_cur=""
            if bs.code=="CAS":
                cr.execute('''select sum(amount)
                                from hq_statement where e_eor='252G-CA' and mode ='hq'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency
                                from hq_statement hq,res_currency as cur where hq.e_eor='252G-CA' and hq.e_currency_id = cur.id ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="FSNS":
                cr.execute('''select sum(amount) from hq_statement where e_eor='28BO'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='28BO' ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="FSN_CW":
                cr.execute('''select sum(amount) from hq_statement where e_eor='28BO' and e_desc like '%Cash%'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='28BO' and hq.e_desc like '%Cash%' ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="NPSC_QSNICH":
                cr.execute('''select sum(amount) from hq_statement where e_eor='252G-NPSC' and e_desc like '%Qsnich%'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='252G-NPSC' and hq.e_desc like '%Qsnich%' ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="NPSC_PMK":
                cr.execute('''select sum(amount) from hq_statement where e_eor='252G-NPSC' and e_desc like '%Pmk%'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='252G-NPSC' and hq.e_desc like '%Pmk%' ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="NPSC_KPPPH_I":
                cr.execute('''select sum(amount) from hq_statement where e_eor='252G-NPSC' and (e_desc like '%KPPH%' or e_desc like '%KPPPH%')  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='252G-NPSC' and (hq.e_desc like '%KPPH%' or hq.e_desc like '%KPPPH%') ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="NPSC_PPHO":
                cr.execute('''select sum(amount) from hq_statement where e_eor='252G-NPSC' and e_desc like '%PPHO%'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='252G-NPSC' and hq.e_desc like '%PPHO%' ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="NPSC_MABA":
                cr.execute('''select sum(amount) from hq_statement where e_eor='252G-NPSC' and e_desc like '%Mabalatan%'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='252G-NPSC' and hq.e_desc like '%Mabalatan%' ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="NPSC_PSU":
                cr.execute('''select sum(amount) from hq_statement where e_eor='252G-NPSC' and e_desc like '%PSU%'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='252G-NPSC' and hq.e_desc like '%PSU%' ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="NPSC_PHL":
                cr.execute('''select sum(amount) from hq_statement where e_eor='252G-NPSC' and e_desc like '%PHL%'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='252G-NPSC' and hq.e_desc like '%PHL%' ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="NPSC_CNTS":
                cr.execute('''select sum(amount) from hq_statement where e_eor='252G-NPSC' and e_desc like '%CNTS%'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='252G-NPSC' and hq.e_desc like '%CNTS%' ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="NPSC_RTA":
                cr.execute('''select sum(amount) from hq_statement where e_eor='252G-NPSC' and e_desc like '%RTA%'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='252G-NPSC' and hq.e_desc like '%RTA%' ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="NPSC_BIOPATH":
                cr.execute('''select sum(amount) from hq_statement where e_eor='252G-NPSC' and e_desc like '%Biopath%'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='252G-NPSC' and hq.e_desc like '%Biopath%' ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="FCCP":
                cr.execute('''select sum(amount) from hq_statement where e_eor='252B' and e_desc like '%Freezerwork%'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='252B' and hq.e_desc like '%Freezerwork%' ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="MIPR_JUSM":
                cr.execute('''select sum(amount) from hq_statement where e_eor='252G' and e_desc like '%-JUSMAGPHIL%' and e_type='MIPR'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='252G' and hq.e_desc like '%-JUSMAGPHIL%' and hq.e_type='MIPR' ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="MIPR_USAC":
                cr.execute('''select sum(amount) from hq_statement where e_eor='232Z' and e_desc like '%USACE%' and e_type='MIPR'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='232Z' and hq.e_desc like '%USACE%' and hq.e_type='MIPR' ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="TRAN_ENTO":
                cr.execute('''select sum(amount) from hq_statement where e_eor='252G-AF' and e_desc like '%Ento%'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='252G-AF' and hq.e_desc like '%Ento%'  ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="TRAN_MAV":
                cr.execute('''select sum(amount) from hq_statement where e_eor='252G-AF' and e_desc like '%Service%'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='252G-AF' and hq.e_desc like '%Service%'  ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="CB_PAV":
                cr.execute('''select sum(amount) from hq_statement where e_eor='252G' and e_desc like '%PAVRU%'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='252G' and hq.e_desc like '%PAVRU%'  ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="CB_COMM":
                cr.execute('''select sum(amount) from hq_statement where e_eor='233Z' and e_desc like '%Comm%'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='233Z' and hq.e_desc like '%Comm%'  ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="LEAS_WH":
                cr.execute('''select sum(amount) from hq_statement where e_eor='XX' and e_desc like '%XX%'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='xx' and hq.e_desc like '%xx%'  ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="LEAS_FF":
                cr.execute('''select sum(amount) from hq_statement where e_eor='232Z' and e_desc like '%Leasing freezer%'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='232Z' and hq.e_desc like '%Leasing freezer%' ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="UTI_FF":
                cr.execute('''select sum(amount) from hq_statement where e_eor='2500' and e_desc like '%Electricity%'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='2500' and hq.e_desc like '%%Electricity%%' ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="BPA_WC":
                cr.execute('''select sum(amount) from hq_statement where e_eor='22NL' and e_desc like '%Shipping service%'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='22NL' and hq.e_desc like '%Shipping service%' ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="BPA_FEDX":
                cr.execute('''select sum(amount) from hq_statement where e_eor='XX' and e_desc like '%XX%'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='xx' and hq.e_desc like '%xxx%' ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="TRANPO":
                cr.execute('''select sum(amount) from hq_statement where e_desc like '%Transpo%' ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_desc like '%Transpo%' ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="CB_TAXI":
                cr.execute('''select sum(amount) from hq_statement where e_eor='22NL' and e_desc like '%Taxi%'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='22NL' and hq.e_desc like '%Taxi%'  ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="DNA_SERV":
                cr.execute('''select sum(amount) from hq_statement where e_eor='252G' and e_desc like '%DNA sequencing%'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='252G' and hq.e_desc like '%DNA sequencing%' ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="SERV_PM_OUT":
                cr.execute('''select sum(amount) from hq_statement where e_desc like '%PMCS%'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_desc like '%PMCS%'  ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="RENOV":
                cr.execute('''select sum(amount) from hq_statement where e_eor='252G-R'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='252G-R' ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="PR_LOG":
                cr.execute('''select sum(amount) from hq_statement where e_eor ='2600' and e_desc like '%Transfer upfront%' and e_type ='MIPR'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='2600' and hq.e_desc like '%Transfer upfront%' and hq.e_type='MIPR'  ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="TRAN_VETMED":
                cr.execute('''select sum(amount) from hq_statement where e_eor='252G-AF' and e_desc like '%Service by%'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='252G-AF' and hq.e_desc like '%Service by%'  ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="TRAN_ENTO_TXC":
                cr.execute('''select sum(amount) from hq_statement where e_eor='26EB-L' and e_desc like '%Mosquito%'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='26EB-L' and hq.e_desc like '%Mosquito%'  ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="SUP_DMLSS":
                cr.execute('''select sum(amount) from hq_statement where e_eor='2600' and e_desc like '%DMLSS%' and e_type='MIPR'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='2600' and hq.e_desc like '%DMLSS%' and hq.e_type='MIPR'  ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="SUP_LAB":
                cr.execute('''select sum(amount) from hq_statement where e_eor='26EB-L' and e_desc like '%XX%'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='26EB-L' and hq.e_desc like '%XX%'  ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="SUP_CLINIC":
                cr.execute('''select sum(amount) from hq_statement where e_eor='26EB-C' and e_desc like '%XX%'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='26EB-C' and hq.e_desc like '%XX%'  ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="SUP_OFFICE":
                cr.execute('''select sum(amount) from hq_statement where e_eor='26EB-O' ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='26EB-O'  ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)

            #unmatch
            elif bs.code=="GAS":
                cr.execute('''select sum(e_amount) from hq_statement where e_eor='26EB-L' and e_desc like '%CO2 Gas%' and mode='local' ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='26EB-L' and hq.e_desc like '%CO2 Gas%' and hq.mode='local' ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="DRYICE":
                cr.execute('''select sum(e_amount) from hq_statement where e_eor='26EB-L' and e_desc like '%Dry Ice%' and mode='local'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                                hq.e_eor='26EB-L' and hq.e_desc like '%Dry Ice%' and hq.mode='local' ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="HJF":
                cr.execute('''select sum(e_amount) from hq_statement where e_eor='HJF' and mode='local'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                              hq.e_eor='HJF' and hq.mode='local'  ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="GNV":
                cr.execute('''select sum(e_amount) from hq_statement where e_eor='GNV' and mode='local'  ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                               hq.e_eor='GNV' and hq.mode='local' ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="TDY_VIRO":
                cr.execute('''select sum(amount) from hq_statement where mode='hq' and type='TDY' and fy_id IN(select id from apc_fiscalyear where active = 't') ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                              hq.mode='hq' and hq.type='TDY' and hq.fy_id IN(select id from apc_fiscalyear where active = 't')  ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)
            elif bs.code=="TDY_COAG":
                cr.execute('''select sum(e_amount) from hq_statement where mode='local' and type='TDY' and fy_id IN(select id from apc_fiscalyear where active = 't') ''')
                amt = map(lambda x:x[0] , cr.fetchall())
                amt=(amt and amt[0] or 0.0)
                cr.execute('''select distinct cur.code as currency from hq_statement hq,res_currency as cur where hq.e_currency_id = cur.id and
                              hq.mode='local' and hq.type='TDY' and hq.fy_id IN(select id from apc_fiscalyear where active = 't')   ''')
                amt_cur = map(lambda x:x[0] , cr.fetchall())
                amt_cur=(amt_cur and amt_cur[0] or 0.0)

            if amt_cur=="USD":
                amt_usd=amt
            else:
                amt_other=amt

            vals[bs.id]={
                "amount_usd": amt_usd,
                "amount_other": amt_other,
                "currency": amt_cur,
            }
        return vals

    _columns={
        "code": fields.char("Code",size=64,required=True),
        "name": fields.char("Name",size=64,required=True,select=1),
        "formular_eor": fields.char("Eor",size=64,select=1),
        "formular_desc": fields.char("Item Desc.",size=64,select=1),
        "formular_pr_type": fields.char("PR Type",size=64,select=1),
        "amount_usd": fields.function(amount,method=True,type="float",string="Amount USD",multi="context"),
        "amount_other": fields.function(amount,method=True,type="float",string="Amount Others",multi="context"),
        "currency": fields.function(amount,method=True,type="char",string="Currency",multi="context"),
        #"currency_id": fields.many2one("res.currency","Currency"),
        "from_hq_budget": fields.selection([("hq","HQ"),("local","Local")],"From HQ Budget",required=True),
        "fy_update_date": fields.char("FY update date",size=64,select=1),
        "note" :fields.text('Note'),
        "active": fields.boolean("Active")
    }

    def _currency(self,cr,uid,context={}):
        user = self.pool.get('res.users').browse(cr,uid,uid)
        company=user.company_id
        return context.get('currency_id',company.currency_id.id)

    _defaults={
        'active':lambda *a : True,
        'from_hq_budget':lambda *a : 'hq',
    }
budget_summary()

class apc_fiscalyear(osv.osv):
    _name="apc.fiscalyear"
    _columns={
        "name": fields.char("Name",size=64,required=True),
        "date_from": fields.date("Date From",required=True),
        "date_to": fields.date("Date To",required=True),
        "active": fields.boolean("Active",select=1),
    }
    _defaults={
        'active':lambda *a : True,
    }
apc_fiscalyear()

class apc_category(osv.osv):
    _name="apc.category"
    _columns={
        "name": fields.char("Name",size=64),
        "project_line": fields.char("Project Line",size=64),
    }
apc_category()

class apc(osv.osv):
    _name="apc"

    def _project_apc_list(self,cr,uid,ids,name,arg,contect={}):
        vals={}
        apc_proj={}
        apc_proj_name={}
        for apc in self.browse(cr,uid,ids):
            cr.execute("select distinct(project_id) from apc_project where apc_id=%d"%apc.id)
            res=cr.fetchall()
            apc_proj = map(lambda x:x[0],res)
            if apc_proj:
                cr.execute("select distinct(name) from project where active=True and id in %s ",(tuple(apc_proj),))
                res3 = cr.fetchall()
                res3 = map(lambda x:x[0],res3)
                if res3:
                    apc_proj_name = '/'.join(str(v) for v in res3)
            vals[apc.id]=apc_proj_name or 'x'
        return vals

    def _show_detail(self,cr,uid,ids,name,arg,context={}):
        user=self.pool.get("res.users").browse(cr,uid,uid)
        dept_id=user.employee_id and user.employee_id.department_id.id or False
        vals={}
        for apc in self.browse(cr,uid,ids):
            vals[apc.id]=apc.department_id.id==dept_id
        return vals

    def target_e(self,cr,uid,ids,name,arg,context={}):
        vals={}
        for apc in self.browse(cr,uid,ids):
            amt=0.0
            for adj in apc.target_adjusts:
                amt+=adj.adjust
            vals[apc.id]=amt
        return vals

    def target_hq(self,cr,uid,ids,name,arg,context={}):
        vals={}
        for apc in self.browse(cr,uid,ids):
            amt=0.0
            for adj in apc.target_hq_adjusts:
                amt+=adj.adjust
            vals[apc.id]=amt
        return vals

    def transferring(self,cr,uid,ids,name,arg,context={}):
        vals={}
        for apc in self.browse(cr,uid,ids):
            hq ='''%HQ%'''
            cr.execute('''select sum(dis.amount/cr.rate) from apc a,apc_distrib dis,purchase_request pr,res_currency_rate cr where a.id=dis.apc_id and dis.pr_id = pr.id and pr.doc_no like '%s' and pr.currency_id = cr.currency_id and a.id =%s '''%(hq,apc.id))
            amt = map(lambda x:x[0] , cr.fetchall())
            amt_pr = (amt and amt[0] or 0.0)

            cr.execute('''select sum(dis.amount) from apc a,apc_distrib dis,tdy_request tdy where a.id=dis.apc_id and dis.tdy_id = tdy.id and tdy.doc_no like '%s' and a.id =%s '''%(hq,apc.id))
            amt = map(lambda x:x[0] , cr.fetchall())
            amt_tdy = (amt and amt[0] or 0.0)

            amt_transf = amt_pr+amt_tdy
            vals[apc.id]=amt_transf
        return vals

    def commit_hq(self,cr,uid,ids,name,arg,context={}):
        vals={}
        for apc in self.browse(cr,uid,ids):
            amt = 0.0
            amt_comhq =0.0
            cr.execute('''select sum(amount) from hq_statement where apc_id=%s '''%(apc.id))
            amt = map(lambda x:x[0] , cr.fetchall())
            amt_comhq=(amt and amt[0] or 0.0)
            vals[apc.id]=amt_comhq
        return vals

    def commit_e(self,cr,uid,ids,name,arg,context={}):
        vals={}
        for apc in self.browse(cr,uid,ids):
            vals[apc.id]= (apc.commit_hq+apc.transferring) or 0.0
        return vals

    def curbal_hq(self,cr,uid,ids,name,arg,context={}):
        vals={}
        for apc in self.browse(cr,uid,ids):
            vals[apc.id]= (apc.target_hq-apc.commit_hq) or 0.0
        return vals

    def curbal_e(self,cr,uid,ids,name,arg,context={}):
        vals={}
        for apc in self.browse(cr,uid,ids):
            vals[apc.id]= (apc.target_hq-apc.commit_e) or 0.0
        return vals

    def _get_apc_project(self,cr,uid,ids,context=None):
        result = {}
        for apc_project_id in self.pool.get("apc.project").browse(cr,uid,ids):
            if apc_project_id.apc_id:

                result[apc_project_id.apc_id.id] = True
        return result.keys()

    def _get_apc_prl(self,cr,uid,ids,context=None):
        result = {}
        for prl_id in self.pool.get("purchase.request.line").browse(cr,uid,ids):

            for apc_id in prl_id.pr_id.apcs:
                print apc_id
                result[apc_id.id] = True
        return result.keys()

    _STORE_DATA ={
                'apc.project' : (lambda self,cr,uid,ids,context={}:ids,
                ['_project_apc_list'],50)
    }

    _columns={
        "sequence" : fields.integer("Sequence"),
        "name": fields.char("Name",size=64,required=True,select=1),
        "code": fields.char("Code",size=64,select=1),
        "category_id": fields.many2one("apc.category","Category",required=True,select=1),
        "fiscalyear_id": fields.many2one("apc.fiscalyear","Fiscal Year",required=True,select=1),
        "allot_no": fields.char("Allotment No",size=64),
        "amsco": fields.char("AMSCO",size=64),
        "station_no": fields.char("Station No",size=64),
        "target_e": fields.function(target_e,method=True,type="float",string="Target(E)"),
        "target_hq": fields.function(target_hq,method=True,type="float",string="Target(HQ)"),
        "curbal": fields.float("curbal(unuse)"),
        "curbal_e": fields.function(curbal_e,method=True,type="float",string="Curbal(E)"),
        "curbal_hq": fields.function(curbal_hq,method=True,type="float",string="Curbal(HQ)"),
        "commit_e": fields.function(commit_e,method=True,type="float",string="Commit(E)"),
        "transferring": fields.function(transferring,method=True,type="float",string="Transferring"),
        "commit_hq": fields.function(commit_hq,method=True,type="float",string="Commit(HQ)"),
        "lines": fields.one2many("apc.entry","apc_id","Entries"),
        "projects": fields.one2many("apc.project","apc_id","Project Allocation"),
        "department_id": fields.many2one("department","Department"),
        "target_adjusts": fields.one2many("target.adjust","apc_id","Target Adjustment"),
        "target_hq_adjusts": fields.one2many("target.hq.adjust","apc_id","Target HQ Adjustment"),
        "entries": fields.one2many("apc.entry","apc_id","APC Entries"),
        "show_detail": fields.function(_show_detail,method=True,type="boolean"),
        "note" :fields.text('Remark I'),
        "note2" :fields.text('Remark II'),
        "active": fields.boolean("Active",select=1),
        "project_apc_list": fields.function(_project_apc_list,method=True,type="text",string="Projects",select=2
           ,store={
                    'apc.project': (_get_apc_project, None , 10),
                    'purchase.request.line': (_get_apc_prl, None , 10),
                    'apc': (lambda self, cr, uid, ids, c={}: ids, None, 20),
                }
        ),
    }

    _defaults={
        'active':lambda *a : True,
    }

    def copy(self,cr,uid,id,default=[],context={}):
        default.update({
            "lines":[],
            #"projects":[],
            "entries":[],
        })
        return super(apc,self).copy(cr,uid,id,default,context)

    def name_get(self,cr,uid,ids,context={}):
        res=[]
        for apc in self.browse(cr,uid,ids):
            res.append((apc.id,"%s %s %s [%s]"%(apc.code,apc.category_id.name,apc.fiscalyear_id.name,apc.name or "")))
        return res

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=80):
        if not args:
            args=[]
        if not context:
            context={}
        if name:
            ids = self.search(cr, uid, [('code', '=', name)] + args, limit=limit, context=context)
            if not ids:
                ids = self.search(cr, uid, [('name', operator, name)] + args, limit=limit, context=context)
        else:
            ids = self.search(cr, uid, args, limit=limit, context=context)
        return self.name_get(cr, uid, ids, context)
apc()

class target_adjust(osv.osv):
    _name="target.adjust"
    _columns={
        "name": fields.char("Description",size=64,required=True),
        "sequence": fields.integer("Sequence",required=True),
        "adjust": fields.float("Adjust",required=True),
        "date": fields.date("Date",required=True),
        "apc_id": fields.many2one("apc","APC",required=True,ondelete="cascade"),
    }
    _defaults={
        "sequence": lambda *a: 1,
        "date": lambda *a: time.strftime("%Y-%m-%d"),
    }
target_adjust()

class target_hq_adjust(osv.osv):
    _name="target.hq.adjust"
    _columns={
        "name": fields.char("Description",size=64,required=True),
        "sequence": fields.integer("Sequence",required=True),
        "adjust": fields.float("Adjust",required=True),
        "date": fields.date("Date",required=True),
        "apc_id": fields.many2one("apc","APC",required=True,ondelete="cascade"),
    }
    _defaults={
        "sequence": lambda *a: 1,
        "date": lambda *a: time.strftime("%Y-%m-%d"),
    }
target_hq_adjust()

class apc_project(osv.osv):
    _name="apc.project"
    _columns={
        "name": fields.char("Name",size=64),
        "apc_id": fields.many2one("apc","APC",required=True),
        "project_id": fields.many2one("project","Project",required=True),
        "target": fields.float("Target"),
    }
apc_project()

class eor(osv.osv):
    _name="eor"
    _order="code"
    #XXX : add discription here

    def _full_name(self,cr,uid,ids,name,arg,context={}):
        vals={}
        for eor in self.browse(cr,uid,ids):
            name=""
            if eor.parent_id:
                name+=eor.parent_id.name+"/"
            name+=eor.name
            vals[eor.id]=name
        return vals

    _columns={
        "name": fields.char("Name",size=64,required=True,select=1),
        "code": fields.char("Code",size=16,select=1),
        "parent_id": fields.many2one("eor","Parent"),
        "full_name": fields.function(_full_name,method=True,type="char",string="Name"),
        "active":fields.boolean('Active',select=1),
    }
    _defaults={
        'active':lambda *a : 1,
    }

    def name_get(self,cr,uid,ids,context={}):
        res=[]
        for eor in self.browse(cr,uid,ids):
            res.append((eor.id,eor.code or "N/A"))
        return res

    def name_search(self,cr,uid,name,args=None,operator='ilike',context={},limit=80):
        ids=self.search(cr,uid,[('code',operator,name)])
        if not ids:
            ids=self.search(cr,uid,[('name',operator,name)])
        return self.name_get(cr,uid,ids,context)
eor()

class apc_entry(osv.osv):
    _name="apc.entry"

    def _doc_no(self,cr,uid,ids,name,arg,context={}):
        #print "_doc_no"
        vals={}
        for ent in self.browse(cr,uid,ids):
            doc_no="N/A"
            if ent.pr_id:
                doc_no=ent.pr_id.doc_no
            elif ent.tdy_id:
                doc_no=ent.tdy_id.doc_no
            vals[ent.id]=doc_no
        return vals

    def _get_type(self,cr,uid,ids,name,arg,context={}):
        #print "_get_type"
        vals={}
        for ent in self.browse(cr,uid,ids):
            type="N/A"
            if ent.pr_id:
                type=ent.pr_id.type
            elif ent.tdy_id:
                type="TDY"
            vals[ent.id]=type
        return vals

    def _apc_eor(self,cr,uid,ids,name,arg,context={}):
        vals={}
        for ent in self.browse(cr,uid,ids):
            vals[ent.id]="%s-%s"%(ent.apc_id.code,ent.eor_id.code)
        return vals

    def _apc_type(self,cr,uid,ids,name,arg,context={}):
        vals={}
        for ent in self.browse(cr,uid,ids):
            vals[ent.id]="%s-%s"%(ent.apc_id.code,ent.type)
        return vals

    def _apc_type_eor(self,cr,uid,ids,name,arg,context={}):
        vals={}
        for ent in self.browse(cr,uid,ids):
            vals[ent.id]="%s-%s-%s"%(ent.apc_id.code,ent.type,ent.eor_id.code)
        return vals

    _columns={
        "name": fields.char("Description",size=64,required=True,select=True),
        "pr_id": fields.many2one("purchase.request","PR"),
        "tdy_id": fields.many2one("tdy.request","TDY"),
        "apc_id": fields.many2one("apc","APC",required=True,select=True),
        "date": fields.date("Date",required=True,select=True),
        "fiscalyear_id": fields.related("apc_id","fiscalyear_id",type="many2one",relation="apc.fiscalyear",string="FY",readonly=True,select=True),
        "category_id": fields.related("apc_id","category_id",type="many2one",relation="apc.category",string="Categ",readonly=True,select=True),
        "curbal": fields.related("apc_id","curbal",type="float",string="Curbal",readonly=True),
        "eor_id": fields.many2one("eor","EOR",select=True), # can be null when auto create from tdy
        "commit": fields.float("Commit ($)",select=2),
        "used": fields.float("Used ($)",select=2),
        "voucher": fields.char("Voucher#",size=64,select=2),
        "doc_no": fields.function(_doc_no,method=True,type="char",size=64,string="Document No",store=True,select=True),
        "type": fields.function(_get_type,method=True,type="char",size=64,string="Type",store=True,select=True),
        "sequence": fields.integer("Seq",select=2),
        "apc_eor": fields.function(_apc_eor,method=True,type="char",size=64,string="APC/EOR",store=True,select=True),
        "apc_type": fields.function(_apc_type,method=True,type="char",size=64,string="APC/Type",store=True,select=True),
        "apc_type_eor": fields.function(_apc_type_eor,method=True,type="char",size=64,string="APC/Type/EOR",store=True,select=True),
        #"notes": fields.many2one("apc","Notes-I"),
        "notes": fields.text("apc","Notes-I"),
        "notes2": fields.text("Notes-II"),
        "notes3": fields.text("Notes-III"),
        "projects": fields.one2many("apc.entry.project","entry_id","Projects"),
        "sites": fields.one2many("apc.entry.site","entry_id","Sites"),
    }

    def _dfl_name(self,cr,uid,context={}):
        #print "_dfl_name",context
        emp_id=context.get("requester")
        if not emp_id:
            return False
        emp=self.pool.get("employee").browse(cr,uid,emp_id)
        return emp.full_name

    _defaults={
        "date": lambda *a: time.strftime("%Y-%m-%d"),
        "name": _dfl_name,
        "sequence": lambda *a: 1,
    }

    def copy(self,cr,uid,id,default=[],context={}):
        default.update({
           # "curbal":[],
        })
        return super(apc_entry,self).copy(cr,uid,id,default,context)

    def _check_bal(self,cr,uid,ids):
        #for ent in self.browse(cr,uid,ids):
        #    if ent.curbal<0:
        #        return False
        return True

    _constraints=[
        (_check_bal,"Insufficient funds in APC",[]),
    ]

    def update_dept_info(self,cr,uid,ids,context={}):
        #print "update_dept_info"
        for ent in self.browse(cr,uid,ids):
            if ent.pr_id:
                cr.execute("delete from apc_entry_project where entry_id=%d",(ent.id,))
                cr.execute("delete from apc_entry_site where entry_id=%d",(ent.id,))
                pr=ent.pr_id
                if not pr.total:
                    continue
                projs={}
                sites={}
                for line in pr.lines:
                    if line.eor_id.code!=ent.eor_id.code:
                        continue
                    for dist in line.projects:
                        amt=line.subtotal*dist.percent/100.0
                        projs[dist.project_id.id]=projs.get(dist.project_id.id,0.0)+amt
                        sites[dist.site_id]=sites.get(dist.site_id,0.0)+amt
                vals={
                    "projects": [],
                    "sites": [],
                }
                for proj_id,amt in sorted(projs.items()):
                    vals["projects"].append((0,0,{
                        "entry_id": ent.id,
                        "project_id": proj_id,
                        "percent": round(100.0*amt/pr.total),
                        "amount": ent.commit*amt/pr.total,
                    }))
                for site_name,amt in sorted(sites.items()):
                    res=self.pool.get("site").search(cr,uid,[('name','=',site_name)])
                    if not res:
                        #print "Warning: invalid site name %s"%site_name
                        continue
                    site_id=res[0]
                    vals["sites"].append((0,0,{
                        "entry_id": ent.id,
                        "site_id": site_id,
                        "percent": round(100.0*amt/pr.total),
                        "amount": ent.commit*amt/pr.total,
                    }))
                #print "vals",vals
                ent.write(vals)
            elif ent.tdy_id:
                cr.execute("delete from apc_entry_project where entry_id=%d",(ent.id,))
                cr.execute("delete from apc_entry_site where entry_id=%d",(ent.id,))
                tdy=ent.tdy_id
                if not tdy.cost_total:
                    continue
                projs={}
                sites={}
                for dist in tdy.projects:
                    amt=tdy.cost_total*dist.percent/100.0
                    projs[dist.project_id.id]=projs.get(dist.project_id.id,0.0)+amt
                    sites[dist.site_id]=sites.get(dist.site_id,0.0)+amt
                vals={
                    "projects": [],
                    "sites": [],
                }
                for proj_id,amt in sorted(projs.items()):
                    vals["projects"].append((0,0,{
                        "entry_id": ent.id,
                        "project_id": proj_id,
                        "percent": round(100.0*amt/tdy.cost_total),
                        "amount": ent.commit*amt/tdy.cost_total,
                    }))
                for site_name,amt in sorted(sites.items()):
                    res=self.pool.get("site").search(cr,uid,[('name','=',site_name)])
                    if not res:
                        #print "Warning: invalid site name %s"%site_name
                        continue
                    site_id=res[0]
                    vals["sites"].append((0,0,{
                        "entry_id": ent.id,
                        "site_id": site_id,
                        "percent": round(100.0*amt/tdy.cost_total),
                        "amount": ent.commit*amt/tdy.cost_total,
                    }))
                #print "vals",vals
                ent.write(vals)
        return True

    def write(self,cr,uid,ids,vals,context={}):
        res=super(apc_entry,self).write(cr,uid,ids,vals,context)
        if type(ids)==type(1):
            ids=[ids]
        #self.update_dept_info(cr,uid,ids,context) # infinite recursion
        return res

    def create(self,cr,uid,vals,context={}):
        res=super(apc_entry,self).create(cr,uid,vals,context)
        self.update_dept_info(cr,uid,[res],context)
        return res
apc_entry()

class project(osv.osv):
    _name="project"

    def _rec_apcs(self,cr,uid,ids,name,arg,context={}):
        #print "_rec_apcs"
        vals={}
        for proj in self.browse(cr,uid,ids):
            cr.execute("select distinct(apc_id) from apc_project where project_id=%d"%proj.id)
            res=cr.fetchall()
            apc_ids =  map(lambda x:x[0],res)
            if apc_ids:
                cr.execute("select id from apc where active=True and id in %s ",(tuple(apc_ids),))
                res2 = cr.fetchall()
                apc_ids = map(lambda x:x[0],res2)
            vals[proj.id]=apc_ids
        #print vals
        return vals

    _columns={
        "name": fields.char("Project Code",size=64,select=True,required=True),
        "protocol": fields.char("Protocol Name",size=1024,select=True),
        "site_ref": fields.char("Site Reference",size=128,select=True),
        "active": fields.boolean("Active",select=1),
        "notes": fields.text("Notes"),
        "rec_apcs": fields.function(_rec_apcs,method=True,type="many2many",relation="apc",string="Recommended APCs"),
        "department_id": fields.many2one("department","Department",required=True),
    }
    _defaults={
        "active": lambda *a: True,
    }
project()

class site(osv.osv):
    _name="site"
    _columns={
        "name": fields.char("Name",size=64,select=True,required=True),
        "department_id": fields.many2one("department","Department",required=True,select=True),
    }
site()

class apc_entry_project(osv.osv):
    _name="apc.entry.project"
    _columns={
        "entry_id": fields.many2one("apc.entry","APC Entry",required=True,ondelete="cascade"),
        "project_id": fields.many2one("project","Project",required=True,ondelete="cascade"),
        "percent": fields.float("Percent"),
        "amount": fields.float("Amount"),
    }
apc_entry_project()

class apc_entry_site(osv.osv):
    _name="apc.entry.site"
    _columns={
        "entry_id": fields.many2one("apc.entry","APC Entry",required=True,ondelete="cascade"),
        "site_id": fields.many2one("site","Site",required=True,ondelete="cascade"),
        "percent": fields.float("Percent"),
        "amount": fields.float("Amount"),
    }
apc_entry_site()

################################
### WORKFLOW ###################
################################

class wkf_state(osv.osv):
    _name="wkf.state"
    _columns={
        "model_id": fields.many2one("ir.model","Object",required=True,select=1),
        "name": fields.char("Name",size=64,required=True,select=1),
        "sequence": fields.integer("Sequence"),
        "active": fields.boolean("Active"),
    }
    _order="model_id,sequence,name"
    _defaults={
        "active" :lambda *a :True,
        }
wkf_state()

class wkf_decision(osv.osv):
    _name="wkf.decision"

    _columns={
        "model_id": fields.many2one("ir.model","Object",required=True,select=1),
        "name": fields.char("Name",size=64,select=1),
        "conditions": fields.one2many("decision.condition","decision_id","Conditions"),
        "choice_type": fields.selection([("one","One"),("many","Many")],"Choice Type",required=True),
        "interface_type": fields.selection([("buttons","Buttons"),("dialog","Dialog")],"Interface Type",required=True),
        "choice_button": fields.char("Choice Button",size=128),
        "choice_title": fields.char("Choice Title",size=128),
        "choice_field": fields.char("Choice Field",size=128),
        "choices": fields.one2many("decision.choice","decision_id","Choices"),
        "deciders": fields.one2many("decision.decider","decision_id","Deciders"),
        "sequence": fields.integer("Sequence"),
        "menu_waiting": fields.boolean("Show in Waiting Menu"),
    }

    _order="model_id,sequence,name"

    _defaults={
        "choice_type": lambda *a: "one",
        "interface_type": lambda *a: "buttons",
    }

    def buttons_visible(self2,self,cr,uid,ids,names,arg,context={}):
        #print "buttons_visible",ids,names,arg,context
        user=self.pool.get("res.users").browse(cr,uid,uid)
        emp=user.employee_id
        emp_id=emp.id
        vals={}
        dec_ids=self2.search(cr,uid,[('model_id','=',self._name)])
        for obj in self.browse(cr,uid,ids):
            buts=[]
            for dec in self2.browse(cr,uid,dec_ids):
                res=self.pool.get("wkf.waiting").can_decide(self,cr,uid,obj.id,dec.id)
                if not res:
                    continue
                #print "  can_decide",dec.name
                if dec.interface_type=="buttons":
                    for ch in dec.choices:
                        if ch.condition and not eval(ch.condition,{"object":obj}):
                            continue
                        #print "    choice",ch.name
                        buts.append("choice_%d"%ch.id)
                elif dec.interface_type=="dialog":
                    buts.append("decision_%d"%dec.id)
            vals[obj.id]=",".join(buts)
        #print "vals",vals
        return vals

    def record_choice(self2,self,cr,uid,ids,decision_id,decider_id,employee_id,choice_id,user_id):
        #print "record_choice",self._name,ids,decision_id,decider_id,employee_id,choice_id,user_id
        user=self.pool.get("res.users").browse(cr,uid,user_id)
        for obj in self.browse(cr,uid,ids):
            vals={
                "decision_id": decision_id,
                "type": "action",
                "decider_id": decider_id,
                "employee_id": employee_id,
                "choice_id": choice_id,
                "user_id": user_id,
                "signature": user.require_cac and user.cac_name or False,
            }
            obj.write({"history":[(0,0,vals)]})

    def apply_choices(self2,self,cr,uid,ids):
        #print "================================================="
        #print "================================================="
        #print "apply_choices",self._name,ids
        updated_objs=set([])
        dec_ids=self2.search(cr,uid,[("model_id","=",self._name)])
        for obj in self.browse(cr,uid,ids):
            for dec in self2.browse(cr,uid,dec_ids):
                #print "decision",dec.name
                cond_ok=False
                for cond in dec.conditions:
                    if cond.state_from.name!=obj.state:
                        continue
                    if cond.condition and not eval(cond.condition,{"object":obj}):
                        continue
                    cond_ok=True
                    break
                if not cond_ok:
                    continue
                #print "conditions of decision '%s' satisfied"%dec.name
                allowed_decider_ids=set([])
                for decider in dec.deciders:
                    if decider.condition and not eval(decider.condition,{"object":obj}):
                        continue
                    allowed_decider_ids.add(decider.id)
                #print "allowed_decider_ids",allowed_decider_ids
                actions=[]
                for h in reversed(obj.history):
                    if h.decision_id.id!=dec.id:
                        break
                    if h.type=="action":
                        actions.append(h)
                state_to=None
                for ch in dec.choices:
                    if ch.condition and not eval(ch.condition,{"object":obj}):
                        #print "  condition of choice '%s' NOK"%ch.name
                        continue
                    #print "  condition of choice '%s' OK"%ch.name
                    ch_decider_ids=[act.decider_id.id for act in actions if act.choice_id.id==ch.id]
                    #print "ch_decider_ids",ch.name,ch_decider_ids
                    if ch.waiting_type=="one":
                        one=False
                        for decider_id in ch_decider_ids:
                            if decider_id in allowed_decider_ids:
                                one=True
                                break
                        if not one:
                            continue
                    elif ch.waiting_type=="all":
                        all=True
                        for decider_id in allowed_decider_ids:
                            if not decider_id in ch_decider_ids:
                                all=False
                                break
                        if not all:
                            continue
                    elif ch.waiting_type=="none":
                        pass
                    #print "choice %s selected"%ch.name
                    if ch.action:
                        try:
                            exec ch.action in {"object":obj}
                        except Exception,e:
                            raise osv.except_osv("Error",str(e)+"\n"+"(workflow choice #%d)"%ch.id)
                    if not state_to:
                        state_to=ch.state_to.name
                    else:
                        if ch.state_to.name!=state_to:
                            raise osv.except_osv("Error","Selected choices leading to different states (states: %s/%s, decision: %s, choice: %s)"%(state_to,ch.state_to.name,dec.name,ch.name))
                if not state_to:
                    continue
                self.write(cr,uid,obj.id,{"state":state_to})
                obj=self.browse(cr,uid,obj.id) # refresh
                self.pool.get("wkf.constraint").check(self,cr,uid,[obj.id])
                updated_objs.add(obj.id)
        #print "updated_objs",updated_objs
        self2.send_requests(self,cr,uid,list(updated_objs))

    def send_requests(self2,self,cr,uid,ids):
        #print "========================================"
        #print "send_requests",ids
        dec_ids=self2.search(cr,uid,[('model_id','=',self._name)])
        for obj in self.browse(cr,uid,ids):
            for dec in self2.browse(cr,uid,dec_ids):
                cond_ok=False
                for cond in dec.conditions:
                    if cond.state_from.name!=obj.state:
                        continue
                    if cond.condition and not eval(cond.condition,{"object":obj}):
                        continue
                    cond_ok=True
                    break
                if not cond_ok:
                    continue
                #print "conditions of decision '%s' satisfied"%dec.name
                for decider in dec.deciders:
                    print "  PR-0.decider is",decider.name
                    if not decider.send_email:
                        print "   PR-1. don't send email"
                        continue
                    if decider.condition and not eval(decider.condition,{"object":obj}):
                        print "    PR-2.condition not pass"
                        continue
                    emp_id=decider.role_id.find_employee(obj)
                    if not emp_id:
                        raise osv.except_osv("Error","Error sending requests for decision '%s': Employee not found for role %s"%(dec.name,decider.role_id.name))
                    emp=self.pool.get("employee").browse(cr,uid,emp_id)
                    #XXX: Temporary comment
                    if not emp.email_notif or not emp.email:
                        continue
                    def replace(match):
                        expr=match.group(0)[2:-2]
                        res=eval(expr,{"object":obj,"emp":emp})
                        return str(res)
                    email=re.sub("(\[\[.+?\]\])",replace,decider.email)#TODO: if no word will get and errors
                    if not email:
                        raise osv.except_osv("Error","Email body is empty")
                    print "3.sending email to %s..."%emp.email
                    #Fix Sender
                    tools.email_send("noreply-erp@afrims.org",[emp.email],"E-System.afrims.org",email) #weng edit
                    #tools.email_send("noreply@almacom.co.th",["worrawutl.ca@afrims.org","worwear@hotmail.com"],"Request from E-system",email)

                    #test other smtp server
                    #tools.email_send("donotreply@almacom.co.th",["worrawutl.ca@afrims.org","songpon.p@almacom.co.th"],\
                        #"Request from E-System",[])
                    vals={
                        "decision_id": dec.id,
                        "type": "request",
                        "decider_id": decider.id,
                        "employee_id": emp_id,
                    }
                    obj.write({"history":[(0,0,vals)]})
wkf_decision()

class decision_condition(osv.osv):
    _name="decision.condition"
    _columns={
        "decision_id": fields.many2one("wkf.decision","Decision",required=True,ondelete="cascade"),
        "state_from": fields.many2one("wkf.state","From State",required=True),
        "condition": fields.char("Condition",size=128),
    }
decision_condition()

class decision_choice(osv.osv):
    _name="decision.choice"
    _columns={
        "decision_id": fields.many2one("wkf.decision","Decision",required=True,ondelete="cascade"),
        "sequence": fields.integer("Seq",required=True),
        "name": fields.char("Name",size=64,required=True,select=1),
        "condition": fields.char("Condition",size=128),
        "state_to": fields.many2one("wkf.state","To State"),
        "action": fields.char("Action",size=128),
        "confirm": fields.char("Confirm",size=128),
        "next_decision_id": fields.many2one("wkf.decision","Next Decision"),
        "waiting_type": fields.selection([("one","One"),("all","All"),("none","None")],"Waiting Type",required=True),
    }
    _order="decision_id,sequence"
    _defaults={
        "sequence": lambda *a: 1,
        "waiting_type": lambda *a: "one",
    }

    def _check(self,cr,uid,ids):
        for ch in self.browse(cr,uid,ids):
            if not ch.state_to and not ch.next_decision_id:
                return False
        return True

    _constraints=[
        (_check,"Invalid choice line",[]),
    ]
decision_choice()

class wkf_role(osv.osv):
    _name="wkf.role"

    _columns={
        "name": fields.char("Role Name",size=64,required=True),
        "employees": fields.one2many("role.employee","role_id","Employees"),
    }

    def has_role(self,cr,uid,ids,user_id,emp_id,obj=None):
        #print "has_role",ids,emp_id,obj
        if user_id==1:
            return True
        for role in self.browse(cr,uid,ids):
            has_role=False
            for line in role.employees:
                if line.employee_id:
                    if line.employee_id.id==emp_id:
                        has_role=True
                        break
                elif line.code:
                    res=eval(line.code,{"object":obj})
                    if emp_id==res:
                        has_role=True
                        break
                if line.condition:
                    emp=self.pool.get("employee").browse(cr,uid,emp_id)
                    if eval(emp.condition,{"object":obj,"emp":emp}):
                        has_role=True
                        break
            if not has_role:
                return False
        return True

    def find_employee(self,cr,uid,ids,obj=None):
        #print "find_employee",ids,obj
        for role in self.browse(cr,uid,ids):
            #print "role",role.name
            for line in role.employees:
                emp_id=None
                if line.employee_id:
                    emp_id=line.employee_id.id
                elif line.code:
                    try:
                        emp_id=eval(line.code,{"object":obj})
                    except Exception,e:
                        raise osv.except_osv("Error","Invalid code in role '%s': %s"%(role.name,str(e)))
                    if not emp_id:
                        continue
                    if type(emp_id)!=type(1):
                        raise osv.except_osv("Invalid code for role %s"%role.name)
                if line.condition:
                    emp=self.pool.get("employee").browse(cr,uid,emp_id)
                    if not eval(line.condition,{"object":obj,"emp":emp}):
                        continue
                return emp_id
        return None

    def get_users(self,cr,uid,ids,obj=None):
        #print "get_users",ids,obj
        user_ids=set([])
        for role in self.browse(cr,uid,ids):
            #print "role",role.name
            for line in role.employees:
                emp_id=None
                if line.employee_id:
                    emp_id=line.employee_id.id
                elif line.code:
                    try:
                        emp_id=eval(line.code,{"object":obj})
                    except Exception,e:
                        raise osv.except_osv("Error","Invalid code in role '%s': %s"%(role.name,str(e)))
                    if not emp_id:
                        continue
                    if type(emp_id)!=type(1):
                        raise osv.except_osv("Invalid code for role %s"%role.name)
                emp=self.pool.get("employee").browse(cr,uid,emp_id)
                if line.condition:
                    if not eval(line.condition,{"object":obj,"emp":emp}):
                        continue
                for user in emp.users:
                    user_ids.add(user.id)
        #print "user_ids",user_ids
        return list(user_ids)
wkf_role()

class role_employee(osv.osv):
    _name="role.employee"

    _columns={
        "role_id": fields.many2one("wkf.role","Role"),
        "employee_id": fields.many2one("employee","Employee"),
        "code": fields.char("Code",size=128),
        "condition": fields.char("Condition",size=128),
    }

    def _check(self,cr,uid,ids):
        for line in self.browse(cr,uid,ids):
            if not line.employee_id and not line.code:
                return False
        return True

    _constraints=[
        (_check,"Invalid role line",[]),
    ]
role_employee()

class decision_decider(osv.osv):
    _name="decision.decider"
    _columns={
        "name": fields.char("Name",size=64,select=1),
        "decision_id": fields.many2one("wkf.decision","Decision",required=True,ondelete="cascade"),
        "role_id": fields.many2one("wkf.role","Role",required=True),
        "condition": fields.char("Condition",size=128),
        "send_email": fields.boolean("Send Email"),
        "email": fields.text("Email"),
    }
decision_decider()

class wkf_hist(osv.osv):
    _name="wkf.hist"
    _columns={
        "decision_id": fields.many2one("wkf.decision","Decision",required=True,ondelete="cascade"),
        "type": fields.selection([("request","Request"),("action","Action")],"Type"),
        "decider_id": fields.many2one("decision.decider","Decider",required=True),
        "role_id": fields.related("decider_id","role_id",type="many2one",relation="wkf.role",string="Role",readonly=True),
        "employee_id": fields.many2one("employee","Employee"),
        "choice_id": fields.many2one("decision.choice","Choice"),
        "date": fields.datetime("Date"),
        "user_id": fields.many2one("res.users","User"),
        "signature": fields.char("Signature",size=128),
        "pr_id": fields.many2one("purchase.request","PR",ondelete="cascade"),
        "tdy_id": fields.many2one("tdy.request","TDY",ondelete="cascade"),
    }
    _defaults={
        "date": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
    }
wkf_hist()

class wiz_update_view(osv.osv_memory):
    _name="wiz.update.view"

    def button_update(self,cr,uid,ids,context={}):
        #print "button_update",ids,context
        dec_ids=self.pool.get("wkf.decision").search(cr,uid,[])
        models=set([])
        for dec in self.pool.get("wkf.decision").browse(cr,uid,dec_ids):
            models.add(dec.model_id.name)
        #print "models",models
        views={}
        for model in models:
            res=self.pool.get("ir.ui.view").search(cr,uid,[("model","=",model),("type","=","form"),("inherit_id","=",False)])
            if not res:
                raise osv.except_osv("Error","Form view not found for model "+model)
            view_id=res[0]
            views[model]={
                "name": model+".buttons",
                "model": model,
                "type": "form",
                "arch": '<group name="buttons" position="inside">\n<field name="buttons_visible" invisible="1"/>\n',
                "inherit_id": view_id,
            }
        data_id=self.pool.get("ir.model.data").search(cr,uid,[("name","=","wiz_wkf_choice")])[0]
        #print "data_id",data_id
        act_id=self.pool.get("ir.model.data").read(cr,uid,data_id,["res_id"])["res_id"]
        #print "act_id",act_id
        for dec in self.pool.get("wkf.decision").browse(cr,uid,dec_ids):
            states=",".join([cond.state_from.name for cond in dec.conditions])
            if dec.interface_type=="buttons":
                for ch in dec.choices:
                    views[dec.model_id.name]["arch"]+="""<button name="%d.%d" type="action" context="{'decision_id':%d,'choice_id':%d}" states="%s" string="%s" attrs="{'invisible':[('buttons_visible','not contains','choice_%d')]}"/>\n"""%(act_id,ch.id,dec.id,ch.id,states,ch.name,ch.id)
            elif dec.interface_type=="dialog":
                if dec.choice_button:
                    views[dec.model_id.name]["arch"]+="""<button name="%d.%d" type="action" context="{'decision_id':%d}" states="%s" string="%s" attrs="{'invisible':[('buttons_visible','not contains','decision_%d')]}"/>\n"""%(act_id,dec.choices[0].id,dec.id,states,dec.choice_button,dec.id)
        for model in models:
            views[model]["arch"]+="</group>"
        #print "views",views
        for model in models:
            res=self.pool.get("ir.ui.view").search(cr,uid,[("name","=",views[model]["name"])])
            if res:
                self.pool.get("ir.ui.view").write(cr,uid,res[0],views[model])
            else:
                self.pool.get("ir.ui.view").create(cr,uid,views[model])
        return {}
wiz_update_view()

class wkf_constraint(osv.osv):
    _name="wkf.constraint"
    _columns={
        "name": fields.char("Name",size=64),
        "model_id": fields.many2one("ir.model","Model",required=True),
        "state": fields.many2one("wkf.state","State"),
        "code": fields.text("Code",required=True),
    }

    def check(self2,self,cr,uid,ids,context={}):
        #print "check"
        cons_ids=self2.search(cr,uid,[("model_id","=",self._name)])
        for obj in self.browse(cr,uid,ids):
            for cons in self2.browse(cr,uid,cons_ids):
                if cons.state.name!=obj.state:
                    continue
                #print "constraint",cons.name,cons.code
                try:
                    exec cons.code.replace("\r","") in {"object":obj}
                except Exception,e:
                    #print "check failed",str(e)
                    raise osv.except_osv("Error",str(e)+"\n(workflow constraint #%d)"%cons.id)
wkf_constraint()

class wiz_print_wkf(osv.osv_memory):
    _name="wiz.print.wkf"
    _columns={
        "model_id": fields.many2one("ir.model","Model",required=True),
    }
wiz_print_wkf()

class wkf_waiting(osv.osv):
    _name="wkf.waiting"
    _columns={
        "model": fields.char("Model",size=128),
        "res_id": fields.integer("Resource ID",required=True),
        "user_id": fields.many2one("res.users","User",required=True),
        "decision_id": fields.many2one("wkf.decision","Decision",required=True,ondelete="cascade"),
    }

    def update_waiting(self2,self,cr,uid,ids,context={}):
        #print "========================"
        #print "update_waiting",self._name,ids,context
        if type(ids)==type(1):
            ids=[ids]
        dec_ids=self.pool.get("wkf.decision").search(cr,uid,[('model_id','=',self._name)])
        cr.execute("delete from wkf_waiting where model=%s and res_id in %s",(self._name,tuple(ids)))
        for obj in self.browse(cr,uid,ids):
            for dec in self.pool.get("wkf.decision").browse(cr,uid,dec_ids):
                cond_ok=False
                for cond in dec.conditions:
                    if cond.state_from.name!=obj.state:
                        continue
                    if cond.condition and not eval(cond.condition,{"object":obj}):
                        continue
                    cond_ok=True
                    break
                if not cond_ok:
                    #print "skip decision '%s', conditions not satisfied"%dec.name
                    continue
                user_ids=set([])
                for decider in dec.deciders:
                    if decider.condition and not eval(decider.condition,{"object":obj}):
                        continue
                    res=decider.role_id.get_users(obj)
                    for user_id in res:
                        user_ids.add(user_id)
                for user_id in user_ids:
                    vals={
                        "model": self._name,
                        "res_id": obj.id,
                        "user_id": user_id,
                        "decision_id": dec.id,
                    }
                    self2.create(cr,uid,vals)

    def can_decide(self2,self,cr,uid,res_id,dec_id,context={}):
        #print "can_decide",uid,self._name,res_id,dec_id,context
        cr.execute("select id from wkf_waiting where model=%s and res_id=%s and user_id=%s and decision_id=%s",(self._name,res_id,uid,dec_id))
        res=cr.fetchone()
        return res and True or False

    def is_waiting(self2,self,cr,uid,ids,name,arg,context={}):
        #print "is_waiting",self._name,uid,ids,name,arg,context
        vals={}
        for id in ids:
            cr.execute("select wait.id from wkf_waiting wait join wkf_decision dec on dec.id=wait.decision_id where dec.menu_waiting and wait.model=%s and wait.user_id=%s and wait.res_id=%s",(self._name,uid,id))
            res=cr.fetchone()
            vals[id]=res and True or False
        return vals

    def is_waiting_search(self2,self,cr,uid,obj,name,args,context={}):
        #print "==========================="
        #print "is_waiting_search",self._name,uid,obj,name,args,context
        cr.execute("select wait.res_id from wkf_waiting wait join wkf_decision dec on dec.id=wait.decision_id where dec.menu_waiting and wait.model=%s and wait.user_id=%s",(self._name,uid))
        res=cr.fetchall()
        ids=[r[0] for r in res]
        #print "ids",ids
        return [("id","in",ids)]
wkf_waiting()

################################
### ACCESS CONTROL #############
################################

class field_rule(osv.osv):
    _name="field.rule"
    _columns={
        "name": fields.char("Name",size=64,select=1),
        "model_id": fields.many2one("ir.model","Model",required=True,select=1),
        "condition": fields.char("Condition",size=128),
        "states": fields.many2many("wkf.state","field_rule_state","rule_id","state_id","States"),
        "fields_": fields.many2many("ir.model.fields","field_rule_field","rule_id","field_id","Fields"), # can't use 'fields' name in web client
    }

    def fields_editable(self2,self,cr,uid,ids,names,arg,context={}):
        #print "FIELDS_EDITABLE",self._name
        if uid==1:
            fld_ids=self.pool.get("ir.model.fields").search(cr,uid,[("model_id","=",self._name)])
            all_fields=",".join([fld.name for fld in self.pool.get("ir.model.fields").browse(cr,uid,fld_ids)])
            return dict([(obj.id,all_fields) for obj in self.browse(cr,uid,ids)])
        user=self.pool.get("res.users").browse(cr,uid,uid)
        rule_ids=set([])
        for group in user.groups_id:
            for rule in group.field_rules:
                if rule.model_id.name==self._name:
                    rule_ids.add(rule.id)
        rule_ids=list(rule_ids)
        #print "rule_ids",rule_ids
        vals={}
        for obj in self.browse(cr,uid,ids):
            ctx={"object":obj,"user":user,"emp":user.employee_id}
            fields=set([])
            for rule in self2.browse(cr,uid,rule_ids):
                #print "rule",rule.name
                if rule.condition and not eval(rule.condition,ctx):
                    #print "  fail (cond)"
                    continue
                if rule.states and not obj.state in [st.name for st in rule.states]:
                    #print "  fail (state)"
                    continue
                #print "  pass"
                for fld in rule.fields_:
                    fields.add(fld.name)
            vals[obj.id]=",".join(list(fields))
        return vals

    def fields_editable_default(self2,self,cr,uid,state,context={}):
        #print "fields_editable_default",self._name,cr,uid,state,context
        if uid==1:
            fld_ids=self.pool.get("ir.model.fields").search(cr,uid,[("model_id","=",self._name)])
            all_fields=",".join([fld.name for fld in self.pool.get("ir.model.fields").browse(cr,uid,fld_ids)])
            return all_fields
        user=self.pool.get("res.users").browse(cr,uid,uid)
        rule_ids=set([])
        for group in user.groups_id:
            for rule in group.field_rules:
                if rule.model_id.name==self._name:
                    rule_ids.add(rule.id)
        rule_ids=list(rule_ids)
        #print "rule_ids",rule_ids
        vals={}
        fields=set([])
        for rule in self2.browse(cr,uid,rule_ids):
            #print "rule",rule.name
            if rule.states and not state in [st.name for st in rule.states]:
                #print "  fail (state)"
                continue
            for fld in rule.fields_:
                fields.add(fld.name)
        res=",".join(list(fields))
        #print "res",res
        return res
field_rule()

class res_groups(osv.osv):
    _inherit="res.groups"
    _columns={
        "field_rules": fields.many2many("field.rule","group_field_rule","group_id","rule_id","Field Rules"),
    }
res_groups()

class wiz_create_users(osv.osv_memory):
    _name="wiz.create.users"

    def button_create(self,cr,uid,ids,context={}):
        emp_ids=self.pool.get("employee").search(cr,uid,[])
        for emp in self.pool.get("employee").browse(cr,uid,emp_ids):
            if not emp.users:
                login="%s.%s"%(emp.fname,emp.lname[0])
                login=login.lower()
                login=re.sub("[^a-z0-9]",".",login)
                login=login.replace("..",".")
                login=login.replace("..",".")
                #print "login",login
                vals={
                    "name": emp.full_name,
                    "login": login,
                    "password": "1234",
                    "employee_id": emp.id,
                }
                self.pool.get("res.users").create(cr,uid,vals)
        return {}
wiz_create_users()

class res_users(osv.osv):
    _inherit="res.users"

    def _context_fields(self,cr,uid,ids,name,arg,context={}):
        #print "context_fields"
        vals={}
        for user in self.browse(cr,uid,ids):
            emp=user.employee_id
            vals[user.id]={
                "context_employee_id": emp.id,
                "context_section_id": emp.section_id and emp.section_id.id or False,
                "context_department_id": emp.department_id and emp.department_id.id or False,
            }
        #print "vals",vals
        return vals

    _columns={
        "employee_id": fields.many2one("employee","Employee"),
        "cac_name": fields.char("CAC Name",size=128),
        "require_cac": fields.boolean("Require CAC"),
        "context_employee_id": fields.function(_context_fields,method=True,type="integer",string="Employee",multi="context"),
        "context_section_id": fields.function(_context_fields,method=True,type="integer",string="Section",multi="context"),
        "context_department_id": fields.function(_context_fields,method=True,type="integer",string="Department",multi="context"),
    }
res_users()

################################
### PURCHASE REQUEST ###########
################################

class pr_type(osv.osv):
    _name="pr.type"
    _columns={
        "name": fields.char("Name",size=64,required=True,select=1),
        "active" :fields.boolean("Active",select=2),
    }
    _defaults={
        "active": lambda *a : True,
        }
pr_type()

class purchase_request(osv.osv):
    _name="purchase.request"

    def _total(self,cr,uid,ids,name,arg,context={}):
        vals={}
        for pr in self.browse(cr,uid,ids):
            amt=0.0
            for line in pr.lines:
                amt+=line.subtotal
            vals[pr.id]=amt
        return vals

    def _rec_apcs(self,cr,uid,ids,name,arg,context={}):
        vals={}
        for pr in self.browse(cr,uid,ids):
            proj_lines={}
            for line in pr.lines:
                for proj in line.projects:
                    proj_lines.setdefault(proj.project_id.id,[]).append(line)
            msg=""
            proj_ids=sorted(proj_lines.keys())
            for proj in self.pool.get("project").browse(cr,uid,proj_ids):
                lines=", ".join([str(line.sequence) for line in proj_lines[proj.id]])
                apcs=", ".join(["%s-%s"%(apc.code,apc.category_id.name) for apc in proj.rec_apcs]) or "N/A"
                msg+="%s (Item %s): %s\n"%(proj.name,lines,apcs)
            vals[pr.id]=msg
        return vals

    def _get_types(self,cr,uid,context):
        ids=self.pool.get("pr.type").search(cr,uid,[('active','=',True)])
        res=[(t.name,t.name) for t in self.pool.get("pr.type").browse(cr,uid,ids)]
        return res

    def _loa(self,cr,uid,ids,name,arg,context={}):
        vals={}
        for pr in self.browse(cr,uid,ids):
            msg=""
            for ent in pr.apc_entries:
                apc=ent.apc_id
                msg+="%s %s(%s) %s %s\n"%(apc.allot_no or "N/A",apc.amsco or "N/A",ent.eor_id.code,apc.code,apc.station_no or "N/A")
            vals[pr.id]=fmt_loa(msg)
        return vals

    def _buttons_visible(self,cr,uid,ids,names,arg,context={}):
        return self.pool.get("wkf.decision").buttons_visible(self,cr,uid,ids,names,arg,context)

    def _fields_editable(self,cr,uid,ids,names,arg,context={}):
        return self.pool.get("field.rule").fields_editable(self,cr,uid,ids,names,arg,context)

    def _is_waiting(self,cr,uid,ids,name,arg,context={}):
        return self.pool.get("wkf.waiting").is_waiting(self,cr,uid,ids,name,arg,context)

    def _is_waiting_search(self,cr,uid,obj,name,args,context={}):
        return self.pool.get("wkf.waiting").is_waiting_search(self,cr,uid,obj,name,args,context)

    def _get_states(self,cr,uid,context={}):
        ids=self.pool.get("wkf.state").search(cr,uid,[('model_id.name','=',self._name),('active','=',True)])
        states=self.pool.get("wkf.state").browse(cr,uid,ids)
        return [(st.name,st.name) for st in states]

    _EDITABLE={'Draft':[('readonly',False)]}

    _columns={
        "supplier_id": fields.many2one("res.partner","Suggested Supplier",domain=[('supplier','=',True)],select=1,states=_EDITABLE),
        "supplier_code": fields.related("supplier_id","ref",type="char",string="Supplier Code"),
        "name": fields.char("Running No",size=64,required=True,select=2,readonly=False),
        "date": fields.date("Date",required=True,select=True,readonly=True,states=_EDITABLE),
        "state": fields.selection(_get_states,"Status",required=True,select=True),
        "type": fields.selection(_get_types,"PR Type",select=True,states=_EDITABLE),
        "requester_id": fields.many2one("employee","Requester",required=True,select=2,change_default=True),
        "department_id": fields.many2one("department","Department",required=True,select=True,change_default=True),
        "section_id": fields.many2one("section","Section",required=True,select=2,change_default=True),
        "doc_no": fields.char("Document No",size=64,select=True,states=_EDITABLE),
        "doc_no_force": fields.char("FMZ",size=64,select=2,states=_EDITABLE),
        "po_no": fields.char("PO No",size=64,select=2,states=_EDITABLE),
        "purpose": fields.text("Main Purpose",required=True,states=_EDITABLE),
        "description": fields.text("Main Description",states=_EDITABLE),
        "apcs": fields.one2many("apc.distrib","pr_id","APCs"),
        "notes": fields.text("Notes-I"),
        "notes2": fields.text("Notes-II"),
        "notes3": fields.text("Notes-III"),
        "lines": fields.one2many("purchase.request.line","pr_id","Lines",readonly=False,states=_EDITABLE),
        "total": fields.function(_total,method=True,type="float",string="Total"),
        "currency_id": fields.many2one("res.currency","Currency"),
        "rec_apcs": fields.function(_rec_apcs,method=True,type="text",string="Recommended APCs"),
        "received_items": fields.one2many("received.item","pr_id","Received Items",states=_EDITABLE),
        "invoices": fields.one2many("invoice","pr_id","Invoices",states=_EDITABLE),
        "deliveries": fields.one2many("delivery","pr_id","Deliveries",states=_EDITABLE),
        "apc_entries": fields.one2many("apc.entry","pr_id","APC Entries"),
        "loa": fields.function(_loa,method=True,type="text",string="Lines of Accounting"),
        "prod_computer": fields.boolean("Computer"),
        "prod_maintenance": fields.boolean("Computer"),
        "prod_property": fields.boolean("Property"),
        "history": fields.one2many("wkf.hist","pr_id","History",states=_EDITABLE),
        "buttons_visible": fields.function(_buttons_visible,method=True,type="char"),
        "fields_editable": fields.function(_fields_editable,method=True,type="char"),
        "thai_super_id": fields.many2one("employee","Local Supervisor",help="Thai/Local Supervisor",states=_EDITABLE),
        "mil_super_id": fields.many2one("employee","Military Supervisor",states=_EDITABLE),
        "purch_admin_id": fields.many2one("employee","Purchase Admin",required=True,states=_EDITABLE),
        "init_officer_id": fields.many2one("employee","Initiating Officer",required=True,states=_EDITABLE),
        "supply_officer_id": fields.many2one("employee","Supply Officer",states=_EDITABLE),
        "cert_officer_id": fields.many2one("employee","Certifying Officer",required=True,states=_EDITABLE),
        "amendments": fields.one2many("amendment","pr_id","Amendments",states=_EDITABLE),
        "remarks": fields.one2many("remark","pr_id","Remarks"),
        "is_waiting": fields.function(_is_waiting,method=True,type="boolean",fnct_search=_is_waiting_search),
        "use_notes1": fields.text("Notes-I"),
        "use_notes2": fields.text("Notes-II"),
        "use_notes3": fields.text("Notes-III"),
        "use_amount": fields.float("Amount",digits=(16,2)),
        "use_currency_id": fields.many2one("res.currency","Currency"),
        "invoice_ref": fields.char("Inv. No",size=64,select=2,states=_EDITABLE),
        "amount_usd": fields.float("USD",digit=(16,4),select=2,states=_EDITABLE),
    }
    _defaults={
        'name': lambda *a: "/",
        "state": lambda *a: "Draft",
        "requester_id": lambda self,cr,uid,context: self.pool.get("res.users").browse(cr,uid,uid).employee_id.id,
        "date": lambda *a: time.strftime("%Y-%m-%d"),
        "fields_editable": lambda self,cr,uid,context: self.pool.get("field.rule").fields_editable_default(self,cr,uid,"Draft",context),
    }
    _order="name desc"


    def create(self,cr,uid,vals,context={}):
        #print "create",self._name,vals,context
        if not vals.get("name") or vals.get("name")=="/":
            vals["name"]=self.pool.get('ir.sequence').get(cr,uid,'purchase.request')
        # because web client doesn't write read-only fields
        requester_id=vals.get("requester_id")
        if not requester_id:
            user=self.pool.get("res.users").browse(cr,uid,uid)
            requester_id=user.employee_id.id
        emp=self.pool.get("employee").browse(cr,uid,requester_id)
        defaults={
            "department_id": emp.department_id.id,
            "section_id": emp.section_id.id,
            "thai_super_id": emp.section_id.supervisor_id.id,
            "mil_super_id": emp.section_id.mil_supervisor_id.id,
            "init_officer_id": emp.department_id.chief_id.id,
        }
        defaults.update(get_user_defaults(self,cr,uid,"department_id",emp.department_id.id))
        defaults.update(get_user_defaults(self,cr,uid,"section_id",emp.section_id.id))
        defaults.update(get_user_defaults(self,cr,uid,"requester_id",requester_id))
        for k,v in defaults.items():
            if not k in vals:
                vals[k]=v
        #print "PR Create default vals ",vals
        res=super(purchase_request,self).create(cr,uid,vals,context)
        self.pool.get("wkf.waiting").update_waiting(self,cr,uid,[res])
        return res

    def write(self,cr,uid,ids,vals,context={}):
        res=super(purchase_request,self).write(cr,uid,ids,vals,context)
        self.pool.get("wkf.waiting").update_waiting(self,cr,uid,ids)
        return res

    def onchange_requester(self,cr,uid,ids,requester_id):
        if not requester_id:
            return {}
        emp=self.pool.get("employee").browse(cr,uid,requester_id)
        vals={
            "department_id": emp.department_id.id,
            "section_id": emp.section_id.id,
            "thai_super_id": emp.section_id.supervisor_id.id,
            "mil_super_id": emp.section_id.mil_supervisor_id.id,
            "init_officer_id": emp.department_id.chief_id.id,
        }
        # because user default fields in web client...
        vals.update(get_user_defaults(self,cr,uid,"department_id",emp.department_id.id))
        vals.update(get_user_defaults(self,cr,uid,"section_id",emp.section_id.id))
        vals.update(get_user_defaults(self,cr,uid,"requester_id",requester_id))
        return {"value": vals}

    def button_apc_entries(self,cr,uid,ids,context={}):
        entries=[]
        for pr in self.browse(cr,uid,ids):
            if pr.apc_entries:
                raise osv.except_osv("Error","APC entries already exist for this PR")
            if not pr.apcs:
                raise osv.except_osv("Error","No funding source")
            apc_id=pr.apcs[0].apc_id.id # FIXME
            for line in pr.lines:
                vals={
                    "apc_id": apc_id,
                    "date": time.strftime("%Y-%m-%d"),
                    "name": line.name,
                    "eor_id": line.eor_id.id,
                    "commit": 0.0,
                    "used": 0.0,
                }
                entries.append((0,0,vals))
            #print "entries",entries
            self.write(cr,uid,pr.id,{"apc_entries":entries})
        return True

    def copy(self,cr,uid,id,default=None,context={}):
        access=self.pool.get("ir.model.access")
        user=self.pool.get("res.users").browse(cr,uid,uid)
        emp=user.employee_id
        pr=self.browse(cr,uid,id)
        if not access.check_groups(cr,uid,"ac_afrims.group_purch_admin"):
            if pr.requester_id.id!=emp.id:
                raise osv.except_osv("Error","You can only duplicate your own requests")
            #TODO : allow dupplicate user in own section-multi,department

        if not default:
            default={}
        default.update({
            "name": self.pool.get('ir.sequence').get(cr,uid,'purchase.request'),
            "apc_entries": [],
            "history": [],
            "amendments": [],
            "apcs": [],
            "date" : time.strftime("%Y-%m-%d"),
            "state": "Draft",
            "doc_no": False,
            "po_no": False,
            "invoice_ref": "",
            "notes": "",
            "notes2":"",
            "notes3":"",
            "invoice_ref": False,
            "use_notes1": False,
            "use_notes2": False,
            "use_notes3": False,
            "remarks": [],
            "thai_super_id":emp.section_id.supervisor_id and emp.section_id.supervisor_id.id or False,
            "mil_super_id": emp.section_id.mil_supervisor_id and emp.section_id.mil_supervisor_id.id or False,
            "init_officer_id": emp.department_id.chief_id and emp.department_id.chief_id.id or False,
            "requester_id":emp.id,
            #"mil_super_id": [],
            #"thai_super_id": [],
            #"init_officer_id": [],
            #"purch_admin_id": [],
            #"supply_officer_id": [],
            #"cert_officer_id": []
        })

        return super(purchase_request,self).copy(cr,uid,id,default,context)

    def merge(self,cr,uid,ids):
        #print "==========================================="
        #print "==========================================="
        #print "merge",ids
        user=self.pool.get("res.users").browse(cr,uid,uid)
        emp=user.employee_id
        if not emp:
            raise osv.except_osv("Error","No employee for current user!")
        curr_id=None
        purpose=""
        description=""
        lines=[]
        for pr in self.browse(cr,uid,ids):
            purpose+=pr.purpose or ""
            description+=pr.description or ""
            if not curr_id:
                curr_id=pr.currency_id.id
            else:
                if pr.currency_id.id!=curr_id:
                    raise osv.except_osv("Error","Different currencies!")
        vals={
            "date": time.strftime("%Y-%m-%d"),
            "requester_id": emp.id,
            "department_id": emp.department_id.id,
            "section_id": emp.section_id.id,
            "currency_id": curr_id,
            "purpose": purpose,
            "description": description,
        }
        #print "vals",vals
        pr_id=self.create(cr,uid,vals)
        sequence=0
        #merge should check:state
        for pr in self.browse(cr,uid,ids):
            for line in pr.lines:
                sequence+=1
                self.pool.get("purchase.request.line").copy(cr,uid,line.id,{"pr_id":pr_id,"sequence":sequence,"notes": "Merged from "+(pr.name or "")+" of "+(pr.requester_id.full_name or "")})
            pr.write({"state":"Merged"})#XXX :must add state merged in setting
        self.write(cr,uid,[pr_id],{"state":"Draft"})
        return pr_id

    def unlink(self, cr, uid, ids, context=None):
        for req in self.browse(cr,uid,ids):
            if not req.state in ("Draft"):
                raise osv.except_osv('Invalid action !',"Can not delete purchase requests in this state!")
        return super(purchase_request, self).unlink(cr, uid, ids, context=context)
purchase_request()

class purchase_request_line(osv.osv):
    _name="purchase.request.line"

    def name_get(self,cr,uid,ids,context={}):
        res=[]
        for prl in self.browse(cr,uid,ids):
            res.append((prl.id,"(%d) %s"%(prl.sequence,(prl.doc_no or '') + (prl.name and " "+prl.name or ''),)))
        return res

    def _subtotal(self,cr,uid,ids,name,arg,context={}):
        vals={}
        for prl in self.browse(cr,uid,ids):
            vals[prl.id]=prl.qty*prl.price_unit
        return vals

    def _received(self,cr,uid,ids,name,arg,context={}):
        vals={}
        for prl in self.browse(cr,uid,ids):
            qty=0.0
            for ri in prl.received_items:
                qty+=ri.qty
            vals[prl.id]=qty
        return vals

    def _get_fy(self,cr,uid,ids,name,arg,context={}):
        vals={}

        cr.execute("""
            select prl.id, pr.name from
                purchase_request pr,purchase_request_line prl
                where prl.id in %s
                    and prl.pr_id=pr.id
        """,(tuple(ids),))

        res = cr.fetchall()
        reg = re.compile("""PR(\d{2})""")
        fy_cache={}
        for r in res:
            m = reg.match(r[1])
            res_id=False
            if m!=None:
                fy='20%s' % m.groups()[0]
                if not fy_cache.get(fy,False):
                    fy_res = self.pool.get('apc.fiscalyear').search(cr,uid,[('name','=',fy)])
                    if fy_res:
                        res_id=fy_res[0]
                        fy_cache[fy]=fy_res[0]
                else:
                    res_id=fy_cache[fy]

            vals[r[0]]=res_id
        return vals

        for id in ids:
            if id not in res:
                res[id]=False
        return res

    def _get_pr(self, cr, uid, ids, context=None):
        cr.execute("""
            select id from purchase_request_line where pr_id in %s """,(tuple(ids),))
        res = map(lambda x:x[0],cr.fetchall())
        return res

    def _rec_apcs(self,cr,uid,ids,name,arg,context={}):
        vals={}
        for tdy in self.browse(cr,uid,ids):
            projs=set([])
            for proj in tdy.projects:
                projs.add(proj.project_id.id)
            msg=""
            proj_ids=sorted(list(projs))
            for proj in self.pool.get("project").browse(cr,uid,proj_ids):
                apcs=", ".join(["%s-%s"%(apc.code,apc.category_id.name) for apc in proj.rec_apcs]) or "N/A"
                msg+="%s: %s\n"%(proj.name,apcs)
            vals[tdy.id]=msg
        return vals

    def _project_apc_list(self,cr,uid,ids,name,arg,contect={}):
        vals={}
        prl_ids={}
        for prl in self.browse(cr,uid,ids):
            cr.execute("select distinct(project_id) from project_distrib where prl_id=%d"%prl.id)
            res=cr.fetchall()
            prl_ids = map(lambda x:x[0],res)
            if prl_ids:
                cr.execute("select distinct(name) from project where id in %s ",(tuple(prl_ids),))
                res3 = cr.fetchall()
                res3 = map(lambda x:x[0],res3)
                if res3:
                    prl_ids = '/'.join(str(v) for v in res3)
            vals[prl.id]=prl_ids or ''
        #print vals
        return vals

    def _apcs_list(self,cr,uid,ids,name,arg,contect={}):
        vals={}
        for line in self.browse(cr,uid,ids):
            name=''
            for dis in line.pr_id.apcs:
                name=dis.apc_id.name
            vals[line.id]=name
        return vals

    def _get_pr_line_from_pr(self, cr, uid, ids, context={}):
        prl_ids = []

        for pr_id in self.pool.get('purchase.request').browse(cr, uid, ids, context=context):
            cr.execute("""
                    select id from purchase_request_line where pr_id = %s
            """%(pr_id.id))
            prl_ids = map(lambda x:x[0],cr.fetchall())

        return prl_ids

    _STORE_APC={
                'purchase.request.line' : (lambda self,cr,uid,ids,context={}:ids,
                ['apcs'],20)
    }

    _columns={
        "fy_id" : fields.function(_get_fy,method=True,type="many2one",relation="apc.fiscalyear",string="Fiscal Year",
           store={
                    'purchase.request': (_get_pr_line_from_pr, None , 10),
                    'purchase.request.line': (lambda self, cr, uid, ids, c={}: ids, None, 20),
                }
        ),
        "id": fields.integer("prl_id",required=True,select=2),
        "pr_id": fields.many2one("purchase.request","PR",required=True,ondelete="cascade",select=1),
        "type": fields.related("pr_id","type",type="char",string="PR Type",readonly=True,select=1),
        "requester_id": fields.related("pr_id","requester_id",type="many2one",relation="employee",string="Requester",readonly=True,select=1),
        "department_id": fields.related("pr_id","department_id",type="many2one",relation="department",string="Department",readonly=True,select=1),
        "section_id": fields.related("pr_id","section_id",type="many2one",relation="section",string="Section",readonly=True,select=1),
        "doc_no": fields.related("pr_id","doc_no",type="char",string="Doc No",readonly=True,select=1),
        "state": fields.related("pr_id","state",type="char",string="State",readonly=True,select=2),
        "sequence": fields.integer("Sequence",required=True,select=2),
        "name": fields.char("Item Description",size=64,required=True,select=1),
        "product_id": fields.many2one("product.product","Product"),
        "rec_apcs": fields.function(_rec_apcs,method=True,type="text",string="Recommended APCs"),
        "qty": fields.float("Quantity",required=True,select=2),
        "projects": fields.one2many("project.distrib","prl_id","Projects All"),
        "project_apc_list": fields.function(_project_apc_list,method=True,type="text",string="Projects",select=2
           ,store={
                    #'apc.project': (_get_apc_project, None , 10),
                    'purchase.request.line': (lambda self, cr, uid, ids, c={}: ids, None, 20),
                    #'apc': (lambda self, cr, uid, ids, c={}: ids, None, 20),
             }),
        "uom_id": fields.many2one("product.uom","UoM",required=True),
        "purpose": fields.text("Purpose",select=2),
        "eor_id": fields.many2one("eor","EOR",select=1),
        "notes": fields.text("DMLSS",select=2),
        "apc_list": fields.function(_apcs_list,method=True,type="text",string="APCs",store=_STORE_APC,select=2),
        "apcs": fields.one2many("apc.distrib","pr_id","APCs"), # to old field
        "apc_id": fields.many2one("apc","APC",required=True),# to old field
        "apc_entries": fields.one2many("apc.entry","pr_id","APC Entries"),# to old field
        "price_unit": fields.float("Unit Price",select=1),
        "subtotal": fields.function(_subtotal,method=True,type="float",string="Item Total",store=True),
        "received": fields.function(_received,method=True,type="float",string="Received"),
        "received_items": fields.one2many("received.item","prl_id","Received Items"),
        "currency_id" :fields.many2one('res.currency','Currency'),
    }

    _order="pr_id desc,sequence,id desc"

    def _seq(self,cr,uid,context={}):
        #print "_seq",context
        pr_name=context.get("pr")
        if not pr_name:
            return 1
        res=self.pool.get("purchase.request").search(cr,uid,[("name","=",pr_name)])
        if not res:
            return 1
        pr_id=res[0]
        pr=self.pool.get("purchase.request").browse(cr,uid,pr_id)
        if not pr.lines:
            return 1
        return pr.lines[-1].sequence+1

    def _eor(self,cr,uid,context={}):
        #print "_eor",context
        pr_name=context.get("pr")
        if not pr_name:
            return False
        res=self.pool.get("purchase.request").search(cr,uid,[("name","=",pr_name)])
        if not res:
            return False
        pr_id=res[0]
        pr=self.pool.get("purchase.request").browse(cr,uid,pr_id)
        if not pr.lines:
            return False
        return pr.lines[-1].eor_id.id

    def _currency(self,cr,uid,context={}):
        user = self.pool.get('res.users').browse(cr,uid,uid)
        company=user.company_id
        return context.get('currency_id',company.currency_id.id)

    _defaults={
        "currency_id" : _currency,
        "sequence": _seq,
        "eor_id": _eor,
    }

    def copy_data(self, cr, uid, id, default=None, context={}):
        """
            This function will called from parent model ( purchase.request )
        """
        if not default:
            default = {}
        default.update({
            "projects": [],
            "notes": False,

            })
        return super(purchase_request_line, self).copy_data(cr, uid, id, default, context)

    def update_product_info(self,cr,uid,ids,context={}):
        product_obj = self.pool.get('product.product')
        for line in self.browse(cr,uid,ids,context):
            product = line.product_id
            price_unit=product.standard_price or 0.0
            currency_id = product.currency_id and product.currency_id.id or False

            if price_unit and currency_id:
                line.write(
                    {'currency_id':currency_id,'price_unit':price_unit}
                )
        return True

    def create(self,cr,uid,vals,context={}):
        #print "create",vals,context
        if not vals.get("projects") and vals.get("pr_id"):
            pr_id=vals["pr_id"]
            pr=self.pool.get("purchase.request").browse(cr,uid,pr_id)
            if pr.lines:
                projects=[]
                last=pr.lines[-1]
                for proj in last.projects:
                    vals_={
                        "project_id": proj.project_id.id,
                        "site_id": proj.site_id,
                        "percent": proj.percent,
                    }
                    projects.append((0,0,vals_))
                vals["projects"]=projects
        return super(purchase_request_line,self).create(cr,uid,vals,context)

    def onchange_product(self,cr,uid,ids,product_id,partner_id):
        #print "onchange_product"
        if not product_id:
            return {}
        prod=self.pool.get("product.product").browse(cr,uid,product_id)
        uom_id=prod.uom_id.id
        qty=1.0
        vals={
            "name": prod.name_get()[0][1],
            "uom_id": uom_id,
            "qty": qty,
            "eor_id": prod.eor_id.id,
            "currency_id": prod.currency_id and prod.currency_id.id or False
        }
        if partner_id:
            partner=self.pool.get("res.partner").browse(cr,uid,partner_id)
            pl=partner.property_product_pricelist_purchase
            price=pl.price_get(product_id,qty,partner_id,{"uom": uom_id})[pl.id]
            vals["price_unit"]=price and price or prod.standard_price
        else:
            vals["price_unit"]=prod.standard_price
        #print "vals",vals
        return {"value": vals}

    def onchange_qty(self,cr,uid,ids,product_id,partner_id,qty,uom_id):
        #print "onchange_qty"
        if not product_id:
            return {}
        if not partner_id:
            return {}
        if not uom_id:
            return {}
        prod=self.pool.get("product.product").browse(cr,uid,product_id)
        partner=self.pool.get("res.partner").browse(cr,uid,partner_id)
        pl=partner.property_product_pricelist_purchase
        price=pl.price_get(product_id,qty or 1.0,partner_id,{"uom": uom_id})[pl.id]
        vals={
            "price_unit": price and price or prod.standard_price,
        }
        #print "vals",vals
        return {"value": vals}
purchase_request_line()

class apc_distrib(osv.osv):
    _name="apc.distrib"

    def _dfl_amount(self,cr,uid,context):
        #print "_dfl_amount"
        total=context.get("total")
        return total

    def _amount_usd(self,cr,uid,ids,name,arg,context={}):
        vals={}
        cur_usd=self.pool.get("res.currency").search(cr,uid,[("code","=","USD")])[0]
        for dis in self.browse(cr,uid,ids):
            if dis.pr_id:
                currency_id=dis.pr_id.currency_id.id
                prl_id=self.pool.get("purchase.request.line").search(cr,uid,[("pr_id","=",dis.pr_id.id)])[0]
                prl=self.pool.get("purchase.request.line").browse(cr,uid,prl_id)
                currency_id=prl.currency_id.id
            else:
                currency_id=cur_usd
            amt=self.pool.get("res.currency").compute(cr,uid,currency_id,cur_usd,dis.amount)
            vals[dis.id]=amt
        return vals

    _columns={
        "apc_id": fields.many2one("apc","APC",required=True),
        "amount": fields.float("Amount",required=True),
        "amount_usd": fields.function(_amount_usd,method=True,type="float",string="Amount ($)"),
        "funding_id": fields.many2one("apc","Funding Source",required=True),
        "pr_id": fields.many2one("purchase.request","PR",ondelete="cascade"),
        "tdy_id": fields.many2one("tdy.request","TDY"),
        "sponsor_id": fields.many2one("apc","Sponsor"),
        "notes": fields.char("Notes",size=128),
    }
    _defaults={
        "amount": _dfl_amount,
    }
apc_distrib()

class project_distrib(osv.osv):
    _name="project.distrib"

    def _get_site(self,cr,uid,context):
        ids=self.pool.get("site").search(cr,uid,[])
        res=[(site.name,site.name) for site in self.pool.get("site").browse(cr,uid,ids)]
        return res

    def _amount(self,cr,uid,ids,name,args,context={}):
        vals={}
        for dist in self.browse(cr,uid,ids):
            amt=0.0
            if dist.prl_id:
                amt=dist.prl_id.subtotal*dist.percent/100.0
            elif dist.tdy_id:
                amt=dist.tdy_id.cost_total*dist.percent/100.0
            vals[dist.id]=amt
        return vals

    def _fields_editable(self,cr,uid,ids,names,arg,context={}):
        res=self.pool.get("field.rule").fields_editable(self,cr,uid,ids,names,arg,context)
        #print "fields_editable",res
        return res

    _columns={
        "project_id": fields.many2one("project","Project",required=True),
        "site_id": fields.selection(_get_site,"Site",select=1),
        "percent": fields.integer("Percent (%)",required=True),
        #"prl_id": fields.many2one("purchase.request.line","PR Line",ondelete="cascade"),
        "prl_id": fields.many2one("purchase.request.line","PR Line"),
        "tdy_id": fields.many2one("tdy.request","TDY",ondelete="cascade"),
        "amount": fields.function(_amount,method=True,type="float",string="Distrib. Amount",store=True),
        "fields_editable": fields.function(_fields_editable,method=True,type="char"),
    }

    _defaults={
        "fields_editable": lambda self,cr,uid,context: self.pool.get("field.rule").fields_editable_default(self,cr,uid,"Draft",context),
    }

    def _site(self,cr,uid,context={}):
        emp_id=context.get("employee_id")
        if not emp_id:
            return False
        emp=self.pool.get("employee").browse(cr,uid,emp_id)
        return emp.site.name

    def _remain(self,cr,uid,context={}):
        #print "_remain",context
        remain=100
        if context.get('projects', []):
            remain = 100 - reduce(lambda x,y : x+y ,[p[2]['percent'] for p in context['projects']])
            return remain
        return remain

    _defaults={
        "site_id": _site,
        "percent": _remain,
    }
project_distrib()

class received_item(osv.osv):
    _name="received.item"
    _columns={
        "name": fields.char("Name",size=64),
        "pr_id": fields.many2one("purchase.request","PR",required=True,ondelete="cascade"),
        "prl_id": fields.many2one("purchase.request.line","Item",required=True),
        "qty": fields.float("Quantity",required=True),
        "date": fields.date("Date",size=64,required=True),
        "invoice_id": fields.many2one("invoice","Invoice"),
        "notes": fields.text("Notes"),
    }
    _defaults={
        "date": lambda *a: time.strftime("%Y-%m-%d"),
    }
received_item()

class invoice(osv.osv):
    _name="invoice"
    _columns={
        "name": fields.char("Invoice No",size=64,required=True),
        "pr_id": fields.many2one("purchase.request","PR",required=True,ondelete="cascade"),
        "amount": fields.float("Amount",required=True),
        "date": fields.date("Date",size=64,required=True),
        "notes": fields.text("Notes"),
    }
    _defaults={
        "date": lambda *a: time.strftime("%Y-%m-%d"),
    }
invoice()

class delivery(osv.osv):
    _name="delivery"
    _columns={
        "name": fields.char("Name",size=64),
        "pr_id": fields.many2one("purchase.request","PR",required=True,ondelete="cascade"),
        "prl_id": fields.many2one("purchase.request.line","Item",required=True),
        "qty": fields.float("Quantity",required=True),
        "employee_id": fields.many2one("employee","Employee",required=True),
        "date": fields.date("Date",size=64,required=True),
        "notes": fields.text("Notes"),
    }

    def _emp(self,cr,uid,context={}):
        #print "_emp",context
        pr_id=context.get("pr")
        if not pr_id:
            return None
        pr=self.pool.get("purchase.request").browse(cr,uid,pr_id)
        return pr.requester_id.id

    _defaults={
        "date": lambda *a: time.strftime("%Y-%m-%d"),
        "employee_id": _emp,
    }
delivery()

class remark(osv.osv):
    _name="remark"
    _columns={
        "pr_id": fields.many2one("purchase.request","PR",ondelete="cascade"),
        "remark": fields.text("Remark"),
        "user_id": fields.many2one("res.users","User",readonly=True),
        "date": fields.datetime("Date",readonly=True),
    }
    _defaults={
        "date": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
        "user_id": lambda self,cr,uid,context: uid,
    }
remark()

################################
### TDY REQUEST ################
################################

class travel_state(osv.osv):
    _name="travel.state"
    _columns={
        "name": fields.char("Name",size=64,select=True),
        "type": fields.selection([("conus","CONUS"),("oconus","OCONUS")],"Type")
    }
travel_state()

class travel_county(osv.osv):
    _name="travel.county"
    _columns={
        "name": fields.char("Name",size=64,select=True),
        "state_id": fields.many2one("travel.state","State",required=True,select=True),
    }
travel_county()

class travel_locality(osv.osv):
    _name="travel.locality"

    def _max_per_diem(self,cr,uid,ids,name,arg,context={}):
        vals={}
        for loc in self.browse(cr,uid,ids):
            res=0.0
            if loc.rates:
                res=loc.rates[-1].max_per_diem
            vals[loc.id]=res
        return vals

    def _lodging(self,cr,uid,ids,name,arg,context={}):
        vals={}
        for loc in self.browse(cr,uid,ids):
            res=0.0
            if loc.rates:
                res=loc.rates[-1].lodging
            vals[loc.id]=res
        return vals

    def _m_and_i(self,cr,uid,ids,name,arg,context={}):
        vals={}
        for loc in self.browse(cr,uid,ids):
            res=0.0
            if loc.rates:
                res=loc.rates[-1].meals+loc.rates[-1].incidental
            vals[loc.id]=res
        return vals

    _columns={
        "name": fields.char("Name",size=64,select=True),
        "state_id": fields.many2one("travel.state","State",required=True,select=True),
        "county_id": fields.many2one("travel.county","County",select=True),
        "rates": fields.one2many("travel.rate","locality_id"),
        "max_per_diem": fields.function(_max_per_diem,method=True,type="float",string="Max Per Diem"),
        "lodging": fields.function(_lodging,method=True,type="float",string="Lodging"),
        "m_and_i": fields.function(_m_and_i,method=True,type="float",string="M&I"),
    }
travel_locality()

class travel_place(osv.osv):
    _name="travel.place"
    _columns={
        "name": fields.char("Place",size=64,select=True),
        "locality_id": fields.many2one("travel.locality","Locality",required=True,select=True),
    }
travel_place()

class travel_rate(osv.osv):
    _name="travel.rate"
    _columns={
        "name": fields.char("Name",size=64),
        "locality_id": fields.many2one("travel.locality","Locality",select=True),
        "state_id": fields.related("locality_id","state_id",string="State",type="many2one",relation="travel.state",select=True),
        "county_id": fields.related("locality_id","county_id",string="County",type="many2one",relation="travel.county",select=True),
        "start": fields.date("Start"),
        "end": fields.date("End"),
        "lodging": fields.float("Lodging"),
        "meals": fields.float("Meals"),
        "incidental": fields.float("Incidental"),
        "max_per_diem": fields.float("Maximum Per Diem"),
    }
travel_rate()

class tdy_categ(osv.osv):
    _name="tdy.categ"
    _columns={
        "name": fields.char("Name",size=64,required=True,select=1),
        "department_id": fields.many2one("department","Department",required=True,select=1),
        "active" : fields.boolean('Active',select=1),
    }
    _defaults={
        'active':lambda *a:1,
    }
tdy_categ()

class remark_template(osv.osv):
    _name="remark.template"
    _columns={
        "name": fields.text("Remark",required=True),
    }
    _order="name"
remark_template()

class tdy_request(osv.osv):
    _name="tdy.request"

    def _get_fy(self,cr,uid,ids,name,arg,context={}):
        vals={}
        cr.execute("""
        select id,name from tdy_request where id in %s
        """,(tuple(ids),))
        res = cr.fetchall()
        reg = re.compile("""TDY(\d{2})""")
        fy_cache={}
        for r in res:
            m = reg.match(r[1])
            res_id=False
            if m!=None:
                fy='20%s' % m.groups()[0]
                if not fy_cache.get(fy,False):
                    fy_res = self.pool.get('apc.fiscalyear').search(cr,uid,[('name','=',fy)])
                    if fy_res:
                        res_id=fy_res[0]
                        fy_cache[fy]=fy_res[0]
                else:
                    res_id=fy_cache[fy]
            if res_id:
                vals[r[0]]=res_id
        for id in ids:
            if id not in vals:
                vals[id]=False
        return vals

    def _all(self,cr,uid,ids,name,arg,context={}):
        #print "_all"
        vals_={}
        for tdy in self.browse(cr,uid,ids):
            emp=tdy.requester_id
            vals={
                "ssn": emp.emp_type=="MIL" and emp.ssn_account_no or emp.employee_no,
                "position": emp.emp_type in ("FSN","FSN(PSA)") and emp.position or emp.title,
                "pass_name": emp.pass_name and emp.pass_name or emp.fname+" "+emp.lname,
            }
            vals_[tdy.id]=vals
        return vals_

    def _cost(self,cr,uid,ids,name,arg,context={}):
        #print "_cost"
        vals_={}
        for tdy in self.browse(cr,uid,ids):
            stays={}
            i=0
            n=len(tdy.itin_det)
            for st in tdy.itin_det:
                i+=1
                if st.desc in ("Transport","Leave"):
                    if not st.place_from_id.id in stays:
                        stays[st.place_from_id.id]=[{"from":None,"to":None,"first":False,"last":False,"need_lodging":None}]
                    stays[st.place_from_id.id][-1]["to"]=st.date_from
                    if i==n:
                        stays[st.place_from_id.id][-1]["last"]=True
                    place_to_id=st.place_to_id.id
                    if not place_to_id:
                        place_to_id=st.place_from_id.id
                    if not place_to_id in stays:
                        stays[place_to_id]=[]
                    date_to=st.date_to
                    if st.desc=="Leave":
                        d0=datetime.datetime.strptime(date_to,"%Y-%m-%d")
                        d1=d0+datetime.timedelta(days=1)
                        date_to=d1.strftime("%Y-%m-%d")
                    stays[place_to_id].append({"from":date_to,"to":None,"first":i==1,"last":False,"need_lodging":st.need_lodging})
            #print "stays",stays

            msg=""
            amt_per_diem=0.0
            place_ids=stays.keys()
            i=0
            for place in self.pool.get("travel.place").browse(cr,uid,place_ids):
                rate_lodging=place.locality_id.lodging
                rate_m_i=place.locality_id.m_and_i
                for rate in tdy.travel_rates:
                    if rate.place_id.id==place.id:
                        rate_lodging=rate.lodging
                        rate_m_i=rate.m_i
                for stay in stays[place.id]:
                    if not stay["from"] or not stay["to"]:
                        continue
                    i+=1
                    msg+="--- Stay #%d (%s %s->%s) ---\n"%(i,place.name,stay["from"],stay["to"])
                    d0=datetime.datetime.strptime(stay["from"],"%Y-%m-%d")
                    d1=datetime.datetime.strptime(stay["to"],"%Y-%m-%d")
                    num_nights=(d1-d0).days
                    if stay["need_lodging"]:
                        cost_lodging=num_nights*rate_lodging
                        msg+="lodging: %d night(s) at %.2f -> %.2f\n"%(num_nights,rate_lodging,cost_lodging)
                        amt_per_diem+=cost_lodging
                    if stay["first"]:
                        cost_mi_first=0.75*rate_m_i
                        msg+="m&i: first day at .75*%.2f -> %.2f\n"%(rate_m_i,cost_mi_first)
                        amt_per_diem+=cost_mi_first
                    num_full_days=max(0,num_nights-(stay["first"] and 1 or 0))
                    if num_full_days:
                        cost_mi_full=num_full_days*rate_m_i
                        msg+="m&i: %d full day(s) at %.2f -> %.2f\n"%(num_full_days,rate_m_i,cost_mi_full)
                        amt_per_diem+=cost_mi_full
                    if stay["last"]:
                        cost_mi_last=0.75*rate_m_i
                        msg+="m&i: last day at .75*%.2f -> %.2f\n"%(rate_m_i,cost_mi_last)
                        amt_per_diem+=cost_mi_last

            cur_usd=self.pool.get("res.currency").search(cr,uid,[("code","=","USD")])[0]
            amt_travel=0.0
            for tc in tdy.transport_costs:
                amt_travel+=self.pool.get("res.currency").compute(cr,uid,tc.currency_id.id,cur_usd,tc.amount)

            cost_total=0.0
            if tdy.cost_per_diem_man:
                cost_total+=tdy.cost_per_diem_man
            else:
                cost_total+=amt_per_diem
            if tdy.cost_travel_man:
                cost_total+=tdy.cost_travel_man
            else:
                cost_total+=amt_travel
            cost_total+=tdy.cost_other
            cost_total+=tdy.cost_regis

            vals={
                "cost_per_diem": amt_per_diem,
                "cost_travel": amt_travel,
                "cost_total": cost_total,
                "cost_per_diem_details": msg,
            }
            vals_[tdy.id]=vals
        return vals_

    def _rec_apcs(self,cr,uid,ids,name,arg,context={}):
        vals={}
        for tdy in self.browse(cr,uid,ids):
            projs=set([])
            for proj in tdy.projects:
                projs.add(proj.project_id.id)
            msg=""
            proj_ids=sorted(list(projs))
            for proj in self.pool.get("project").browse(cr,uid,proj_ids):
                apcs=", ".join(["%s-%s"%(apc.code,apc.category_id.name) for apc in proj.rec_apcs]) or "N/A"
                msg+="%s: %s\n"%(proj.name,apcs)
            vals[tdy.id]=msg
        return vals

    def _loa(self,cr,uid,ids,name,arg,context={}):
        vals={}
        for tdy in self.browse(cr,uid,ids):
            msg=""
            if tdy.apc_entries:
                for ent in tdy.apc_entries:
                    apc=ent.apc_id
                    msg+="%s %s(%s) %s %s\n"%(apc.allot_no or "N/A",apc.amsco or "N/A",ent.eor_id.code,apc.code,apc.station_no or "N/A")
            else:
                for distrib in tdy.apcs:
                    apc=distrib.apc_id
                    if tdy.per_diem_eor_id and (tdy.cost_per_diem or tdy.cost_per_diem_man):
                        msg+="%s %s(%s) %s %s\n"%(apc.allot_no or "N/A",apc.amsco or "N/A",tdy.per_diem_eor_id.code,apc.code,apc.station_no or "N/A")
                    if tdy.travel_eor_id and (tdy.cost_travel or tdy.cost_travel_man):
                        msg+="%s %s(%s) %s %s\n"%(apc.allot_no or "N/A",apc.amsco or "N/A",tdy.travel_eor_id.code,apc.code,apc.station_no or "N/A")
                    if tdy.regis_eor_id and tdy.cost_regis:
                        msg+="%s %s(%s) %s %s\n"%(apc.allot_no or "N/A",apc.amsco or "N/A",tdy.regis_eor_id.code,apc.code,apc.station_no or "N/A")
            vals[tdy.id]=fmt_loa(msg)
        return vals

    def _buttons_visible(self,cr,uid,ids,names,arg,context={}):
        return self.pool.get("wkf.decision").buttons_visible(self,cr,uid,ids,names,arg,context)

    def _fields_editable(self,cr,uid,ids,names,arg,context={}):
        return self.pool.get("field.rule").fields_editable(self,cr,uid,ids,names,arg,context)

    def _is_waiting(self,cr,uid,ids,name,arg,context={}):
        return self.pool.get("wkf.waiting").is_waiting(self,cr,uid,ids,name,arg,context)

    def _is_waiting_search(self,cr,uid,obj,name,args,context={}):
        return self.pool.get("wkf.waiting").is_waiting_search(self,cr,uid,obj,name,args,context)

    def _get_states(self,cr,uid,context={}):
        ids=self.pool.get("wkf.state").search(cr,uid,[('model_id.name','=',self._name)])
        states=self.pool.get("wkf.state").browse(cr,uid,ids)
        return [(st.name,st.name) for st in states]

    _columns={
        "name": fields.char("Running No",size=64,required=True,select=1),
        "date": fields.date("Date",required=True,select=1),
        "state": fields.selection(_get_states,"Status",required=True,select=True),
        "requester_id": fields.many2one("employee","Requester",required=True,change_default=True,select=1),
        "department_id": fields.many2one("department","Department",required=True,change_default=True,select=1),
        "section_id": fields.many2one("section","Section",required=True,change_default=True,select=2),
        "doc_no": fields.char("Document No",size=64,select=1),
        "po_no": fields.char("PO No",size=64,select=1),
        "purpose": fields.text("Main Purpose",required=True),
        "range": fields.selection([("local","Local"),("inter","International")],"Travel Range",required=True),
        "categ_id": fields.many2one("tdy.categ","TDY Category",required=True),
        "ssn": fields.related("requester_id","ssn_account_no",type="char",string="SSN/Account No.",readonly=True),
        "rank": fields.related("requester_id","rank",type="char",string="Rank Military/Civilian Rank",readonly=True),
        "position": fields.function(_all,method=True,type="char",string="Position title",multi="all"),
        "pass_num": fields.related("requester_id","pass_num",type="char",string="Passport Number",readonly=True),
        "pass_date_issue": fields.related("requester_id","pass_issue_date",type="char",string="Date Of Issue",readonly=True),
        "pass_date_exp": fields.related("requester_id","pass_exp_date",type="char",string="Expiration Date",readonly=True),
        "pass_place_issue": fields.related("requester_id","pass_issue_place",type="char",string="Place Of Issue",readonly=True),
        "pass_name": fields.function(_all,method=True,type="char",string="Passport Name",multi="all"),
        "itin_det": fields.one2many("itinerary.step","tdy_id","Detailed Itinerary"),
        "itin": fields.text("Itinerary",required=True),
        "travel_modes": fields.many2many("travel.mode","tdy_req_travel_modes","tdy_id","mode_id","Travel Modes"),
        "address": fields.text("TDY/Leave Address"),
        "tdy_days": fields.integer("TDY Days",required=True),
        "tdy_location": fields.many2one("travel.place","Main TDY Location",required=True,select=2),
        "conferences": fields.one2many("tdy.conference","tdy_id","Conferences"),
        "advance": fields.boolean("Advance Money"),
        "advance_amount": fields.float("Advance Amount"),
        "projects": fields.one2many("project.distrib","tdy_id","Projects"),
        "apcs": fields.one2many("apc.distrib","tdy_id","APCs"),
        "notes": fields.text("Remarks"),
        "rec_apcs": fields.function(_rec_apcs,method=True,type="text",string="Recommended APCs"),
        "travel_rates": fields.one2many("tdy.rate","tdy_id","Travel Rates"),
        "transport_costs": fields.one2many("transport.cost","tdy_id","Transport Costs"),
        "cost_per_diem": fields.function(_cost,method=True,type="float",string="Per Diem Cost (Computed)",multi="cost"),
        "cost_travel": fields.function(_cost,method=True,type="float",string="Travel Cost (Computed)",multi="cost"),
        "cost_per_diem_man": fields.float("Per Diem Cost (Manual)"),
        "cost_travel_man": fields.float("Travel Cost (Manual)"),
        "cost_other": fields.float("Other Cost"),
        "cost_regis": fields.float("Registration Cost"),
        "cost_total": fields.function(_cost,method=True,type="float",string="Total Cost",multi="cost",store=True),
        "cost_per_diem_details": fields.function(_cost,method=True,type="text",string="Per Diem Cost Details",multi="cost"),
        "apc_entries": fields.one2many("apc.entry","tdy_id","APC Entries"),
        "loa": fields.function(_loa,method=True,type="text",string="Lines of Accounting"),
        "history": fields.one2many("wkf.hist","tdy_id","History"),
        "dep_date": fields.date("Departure Date",required=True,select=2),
        "per_diem_eor_id": fields.many2one("eor","Per Diem EOR"),
        "travel_eor_id": fields.many2one("eor","Travel EOR"),
        "regis_eor_id": fields.many2one("eor","Registration EOR"),
        "other_rate": fields.float("Other rate of per diem"),
        "amendments": fields.one2many("amendment","tdy_id","Amendments"),
        "thai_super_id": fields.many2one("employee","Local Supervisor",help="Thai/Local Supervisor"),
        "mil_super_id": fields.many2one("employee","Military Supervisor"),
        "purch_admin_id": fields.many2one("employee","Purchase Admin",required=True),
        "req_official_id": fields.many2one("employee","Travel-Requesting Official",required=True),
        "app_official_id": fields.many2one("employee","Travel-Approving/Directing Official",required=True),
        "auth_official_id": fields.many2one("employee","Authorizing/Order-issuing Official",required=True),
        "buttons_visible": fields.function(_buttons_visible,method=True,type="char"),
        "fields_editable": fields.function(_fields_editable,method=True,type="char"),
        "is_waiting": fields.function(_is_waiting,method=True,type="boolean",fnct_search=_is_waiting_search),
        "notes1": fields.text("Notes-I"),
        "notes2": fields.text("Notes-II"),
        "notes3": fields.text("Notes-III"),

        "fy_id" : fields.function(_get_fy,method=True,type="many2one",relation="apc.fiscalyear",string="Fiscal Year",
           #store={ 'tdy.request': (lambda self,cr,uid,ids,context={}:ids, ['state','name'], 10) }
           store=True
        ),
    }
    #def _currency(self,cr,uid,context={}):
    #    user = self.pool.get('res.users').browse(cr,uid,uid)
    #    company=user.company_id
    #    return context.get('currency_id',company.currency_id.id)

    def _department(self,cr,uid,context={}):
        dept = self.pool.get('department').browse(cr,uid,department_id)
        dept = dept.department_id
        return context.get('department_id',dept.departmet_id.id)


    #emp=self.pool.get("employee").browse(cr,uid,requester_id)
    _defaults={
        "name": lambda *a: "/",
        "state": lambda *a: "Draft",
        "date": lambda *a: time.strftime("%Y-%m-%d"),
        "requester_id": lambda self,cr,uid,context: self.pool.get("res.users").browse(cr,uid,uid).employee_id.id,
        "department_id": lambda self,cr,uid,context: self.pool.get("res.users").browse(cr,uid,uid).employee_id.department_id.id,
        "section_id": lambda self,cr,uid,context: self.pool.get("res.users").browse(cr,uid,uid).employee_id.section_id.id,
        "fields_editable": lambda self,cr,uid,context: self.pool.get("field.rule").fields_editable_default(self,cr,uid,"Draft",context),
    }

    _order="name desc"

    def onchange_requester(self,cr,uid,ids,requester_id):
        if not requester_id:
            return {}
        emp=self.pool.get("employee").browse(cr,uid,requester_id)
        vals={
            "department_id": emp.department_id.id,
            "section_id": emp.section_id.id,
            "thai_super_id": emp.section_id.supervisor_id.id,
            "mil_super_id": emp.section_id.mil_supervisor_id.id,
            "req_official_id": emp.department_id.chief_id.id,
        }
        # because user default fields in web client...
        vals.update(get_user_defaults(self,cr,uid,"department_id",emp.department_id.id))
        vals.update(get_user_defaults(self,cr,uid,"section_id",emp.section_id.id))
        vals.update(get_user_defaults(self,cr,uid,"requester_id",requester_id))
        return {"value": vals}

    def create(self,cr,uid,vals,context={}):
        #print "CREATE"
        if not vals.get("name") or vals.get("name")=="/":
            vals["name"]=self.pool.get('ir.sequence').get(cr,uid,'tdy.request')
        # because web client doesn't write read-only fields
        requester_id=vals.get("requester_id")
        if not requester_id:
            user=self.pool.get("res.users").browse(cr,uid,uid)
            requester_id=user.employee_id.id
        emp=self.pool.get("employee").browse(cr,uid,requester_id)
        defaults={
            "department_id": emp.department_id.id,
            "section_id": emp.section_id.id,
            "thai_super_id": emp.section_id.supervisor_id.id,
            "mil_super_id": emp.section_id.mil_supervisor_id.id,
            "req_official_id": emp.department_id.chief_id.id,
        }
        defaults.update(get_user_defaults(self,cr,uid,"department_id",emp.department_id.id))
        defaults.update(get_user_defaults(self,cr,uid,"section_id",emp.section_id.id))
        defaults.update(get_user_defaults(self,cr,uid,"requester_id",requester_id))
        for k,v in defaults.items():
            if not k in vals:
                vals[k]=v
        res=super(tdy_request,self).create(cr,uid,vals,context)
        self.pool.get("wkf.waiting").update_waiting(self,cr,uid,[res])
        return res

    def button_apc_entries(self,cr,uid,ids,context={}):
        entries=[]
        for tdy in self.browse(cr,uid,ids):
            if tdy.apc_entries:
                raise osv.except_osv("Error","APC entries already exist for this TDY")
            if not tdy.apcs:
                raise osv.except_osv("Error","No funding source")
            for apc in tdy.apcs:
                vals={
                    "apc_id": apc.apc_id.id,
                    "date": time.strftime("%Y-%m-%d"),
                    "name": tdy.requester_id.full_name,
                    "eor_id": False,
                    "commit": 0.0,
                    "used": 0.0,
                }
                entries.append((0,0,vals))
            #print "entries",entries
            self.write(cr,uid,tdy.id,{"apc_entries":entries})
        return True

    def copy(self,cr,uid,id,default=None,context={}):
        access=self.pool.get("ir.model.access")
        user=self.pool.get("res.users").browse(cr,uid,uid)
        emp=user.employee_id
        tdy=self.browse(cr,uid,id)
        if not access.check_groups(cr,uid,"ac_afrims.group_purch_admin"):
            if tdy.requester_id.id!=emp.id:
                raise osv.except_osv("Error","You can only duplicate your own requests")
        if not default:
            default={}
        default.update({
            "name": self.pool.get('ir.sequence').get(cr,uid,'tdy.request'),
            "apc_entries": [],
            "history": [],
            "amendments": [],
            "apcs": [],
            "state": "Draft",
            "doc_no": False,
            "po_no": False,
            'notes':False,
            "notes1":False,
            "notes2":False,
            "notes3":False,
            "date": time.strftime("%Y-%m-%d"),
            "projects": False,
            "thai_super_id":emp.section_id.supervisor_id and emp.section_id.supervisor_id.id or False,
            "mil_super_id": emp.section_id.mil_supervisor_id and emp.section_id.mil_supervisor_id.id or False,
            "req_official_id": emp.department_id.chief_id and emp.department_id.chief_id.id or False,
            "requester_id":emp.id,
        })
        return super(tdy_request,self).copy(cr,uid,id,default,context)

    def unlink(self, cr, uid, ids, context=None):
        for req in self.browse(cr,uid,ids):
            if not req.state in ("Draft"):
                raise osv.except_osv('Invalid action !',"Can not delete TDY requests in this state!")
        return super(tdy_request, self).unlink(cr, uid, ids, context=context)

    def write(self,cr,uid,ids,vals,context={}):
        res=super(tdy_request,self).write(cr,uid,ids,vals,context)
        self.pool.get("wkf.waiting").update_waiting(self,cr,uid,ids)
        return res
tdy_request()

class tdy_rate(osv.osv):
    _name="tdy.rate"
    _columns={
        "tdy_id": fields.many2one("tdy.request","TDY",required=True,ondelete="cascade"),
        "place_id": fields.many2one("travel.place","Place",required=True),
        "lodging": fields.float("Lodging",required=True),
        "m_i": fields.float("M&I",required=True),
    }
tdy_rate()

class tdy_conference(osv.osv):
    _name="tdy.conference"
    _columns={
        "tdy_id": fields.many2one("tdy.request","TDY",required=True,ondelete="cascade"),
        "name": fields.char("Name Of Conference",size=64,required=True),
        "location": fields.char("Location",size=64,required=True),
        "date": fields.date("Date"),
        "pres_title": fields.char("Title of presentation",size=64),
        "pres_type": fields.selection([("oral","Oral"),("poster","Poster")],"Presentation Type"),
        "cost": fields.float("Regis. Cost"),
        "currency_id": fields.many2one("res.currency","Currency"),
    }
tdy_conference()

class transport_cost(osv.osv):
    _name="transport.cost"

    def _get_mode(self,cr,uid,context={}):
        ids=self.pool.get("travel.mode").search(cr,uid,[])
        res=self.pool.get("travel.mode").browse(cr,uid,ids)
        return [(str(r.id),r.name) for r in res]

    _columns={
        "tdy_id": fields.many2one("tdy.request","TDY",required=True,ondelete="cascade"),
        "mode": fields.selection(_get_mode,"Travel Mode",required=True),
        "amount": fields.float("Amount",required=True),
        "currency_id": fields.many2one("res.currency","Currency",required=True),
    }
transport_cost()

class travel_mode(osv.osv):
    _name="travel.mode"
    _columns={
        "name": fields.char("Name",size=64,required=True),
        "categ1": fields.selection([("C","Commercial"),("G","Government"),("L","Local Transportation")],"Category-1",required=True),
        "categ2": fields.selection([("R","Rail"),("A","Air"),("B","Bus"),("S","Ship"),("V","Vehicle"),("C","Car Rental"),("T","Taxi"),("O","Other")],"Category-2",required=True),
    }
travel_mode()

class itin_desc(osv.osv):
    _name="itin.desc"
    _columns={
        "name": fields.char("Description",size=64,required=True),
    }
itin_desc()

class itinerary_step(osv.osv):
    _name="itinerary.step"

    def _get_mode(self,cr,uid,context={}):
        ids=self.pool.get("travel.mode").search(cr,uid,[])
        res=self.pool.get("travel.mode").browse(cr,uid,ids)
        return [(r.name,r.name) for r in res]

    def _get_desc(self,cr,uid,context={}):
        ids=self.pool.get("itin.desc").search(cr,uid,[])
        res=self.pool.get("itin.desc").browse(cr,uid,ids)
        return [(r.name,r.name) for r in res]

    _columns={
        "tdy_id": fields.many2one("tdy.request","TDY",ondelete="cascade"),
        "date_from": fields.date("From Date",required=True),
        "date_to": fields.date("To Date",required=True),
        "place_from_id": fields.many2one("travel.place","From Place",required=True),
        "place_to_id": fields.many2one("travel.place","To Place"),
        "desc": fields.selection(_get_desc,"Description",required=True),
        "mode": fields.selection(_get_mode,"Travel Mode"),
        "need_lodging": fields.boolean("Need Lodging"),
        "address_id": fields.many2one("res.partner.address","Address"),
    }
    _order="date_from,date_to"

    def _get_date(self,cr,uid,context={}):
        #print "get_date",context
        tdy_name=context.get("tdy")
        if not tdy_name:
            return False
        res=self.pool.get("tdy.request").search(cr,uid,[("name","=",tdy_name)])
        if not res:
            return False
        tdy_id=res[0]
        tdy=self.pool.get("tdy.request").browse(cr,uid,tdy_id)
        if not tdy.itin_det:
            return False
        last=tdy.itin_det[-1]
        return last.date_to

    _defaults={
        "date_from": _get_date,
        "date_to": _get_date,
        "need_lodging": lambda *a: True,
    }

    def onchange_date_from(self,cr,uid,ids,date_from,date_to):
        if date_to:
            return {}
        vals={
            "date_to": date_from,
        }
        return {"value": vals}
itinerary_step()

class amendment(osv.osv):
    _name="amendment"
    _columns={
        "tdy_id": fields.many2one("tdy.request","TDY",ondelete="cascade"),
        "pr_id": fields.many2one("purchase.request","PR",ondelete="cascade"),
        "desc": fields.text("Description",required=True),
        "date": fields.date("Date",required=True),
        "state": fields.selection([("waiting","Waiting"),("done","Done"),("canceled","Canceled")],"Status",required=True),
        "notes": fields.text("Notes"),
    }
    _defaults={
        "date": lambda *a: time.strftime("%Y-%m-%d"),
        "state": lambda *a: "waiting",
    }
amendment()

def download(url):
    try:
        PROXY="http://10.3.10.30:3128"
        proxy=urllib2.ProxyHandler({"http":PROXY})
        opener=urllib2.build_opener(proxy,urllib2.HTTPHandler)
        urllib2.install_opener(opener)
        data=urllib2.urlopen(url).read()
        return data
    except Exception,e:
        raise Exception("Failed to download file: %s\n%s"%(url,str(e)))

class wiz_update_travel(osv.osv_memory):
    _name="wiz.update.travel"

    def button_update(self,cr,uid,ids,context={}):
        def merge(model,vals,key="name"):
            obj=self.pool.get(model)
            res=obj.search(cr,uid,[("name","=",vals[key])])
            if not res:
                return obj.create(cr,uid,vals)
            id=res[0]
            obj.write(cr,uid,id,vals)
            return id

        def import_data(data,type):
            #print "import_data",type
            rd=csv.reader(StringIO.StringIO(data),delimiter=";")
            lines=[line for line in rd]
            states={}
            counties={}
            localities={}
            i=0
            n=len(lines)
            for line in lines:
                i+=1
                #print "line %d/%d"%(i,n),line
                state=line[0]
                locality=line[1]
                lodging=float(line[5])
                meals=float(line[6])
                if type=="conus":
                    max_per_diem=float(line[8])
                    start=line[9]
                    county=line[2]
                else:
                    max_per_diem=float(line[10])
                    start=line[11]
                    county=False
                incidental=max_per_diem-(lodging+meals)
                start=time.strftime("%Y-%m-%d",time.strptime(start,"%m/%d/%Y"))

                state_id=merge("travel.state",{"name":state,"type":type})
                if county:
                    county_id=merge("travel.county",{"name":county,"state_id":state_id})
                else:
                    county_id=None
                locality_id=merge("travel.locality",{"name":locality,"state_id":state_id,"county_id":county_id})
                merge("travel.rate",{"locality_id":locality_id,"lodging":lodging,"meals":meals,"incidental":incidental,"max_per_diem":max_per_diem,"start":start},key="locality_id")

        url_conus="http://www.defensetravel.dod.mil/perdiem/conus2010.zip"
        conus=download(url_conus)
        conus_z=zipfile.ZipFile(StringIO.StringIO(conus))
        name=None
        for n in conus_z.namelist():
            if n.startswith("connow"):
                name=n
                break
        if not name:
            raise Exception("CONUS file not found")
        conus_t=conus_z.open(name).read()
        import_data(conus_t,"conus")

        url_oconus="http://www.defensetravel.dod.mil/perdiem/oconus.zip"
        oconus=download(url_oconus)
        oconus_z=zipfile.ZipFile(StringIO.StringIO(oconus))
        name=None
        for n in oconus_z.namelist():
            if n.startswith("oconus.txt"):
                name=n
                break
        if not name:
            raise Exception("CONUS file not found")
        oconus_t=oconus_z.open(name).read()
        import_data(oconus_t,"oconus")
        return {}
wiz_update_travel()

################################
### STOCK ######################
################################

class product_product(osv.osv):
    _inherit="product.product"
    _columns={
        "eor_id": fields.many2one("eor","EOR"),
        "catalog_use_ok": fields.boolean("Catalog Use",help="This product will be used in catalog",select=1),
        "currency_id" :fields.many2one('res.currency','Currency'),
    }

    def _currency(self,cr,uid,context={}):
        user = self.pool.get('res.users').browse(cr,uid,uid)
        company=user.company_id
        return context.get('currency_id',company.currency_id.id)

    _defaults={
        "currency_id" : _currency,
    }

product_product()

class warehouse(osv.osv):
    _name="warehouse"
    _columns={
        "name": fields.char("Name",size=64,required=True),
        "department_id": fields.many2one("department","Department",required=True),
        "in_items": fields.one2many("in.item","wh_id","Incoming"),
        "out_items": fields.one2many("out.item","wh_id","Outgoing"),
        "int_moves": fields.one2many("int.move","wh_id","Moves"),
        "avail_items": fields.one2many("avail.item","wh_id","Available",readonly=True),
    }
warehouse()

class wh_location(osv.osv):
    _name="wh.location"
    _columns={
        "name": fields.char("Name",size=64,required=True),
        "wh_id": fields.many2one("warehouse","Warehouse",required=True),
    }
wh_location()

class in_item(osv.osv):
    _name="in.item"
    _columns={
        "name": fields.char("Running No",size=64,readonly=True),
        "wh_id": fields.many2one("warehouse","Warehouse",required=True,select=1),
        "container_id": fields.many2one("container","Container",select=1),
        "product_id": fields.many2one("product.product","Product",select=1),
        "lot": fields.char("Lot",size=64,select=1),
        "qty": fields.float("Quantity",select=2),
        "uom_id": fields.many2one("product.uom","UoM",select=2),
        "employee_id": fields.many2one("employee","From Employee",required=True,select=2),
        "date": fields.date("Date",required=True,select=2),
        "location_id": fields.many2one("wh.location","Location",required=True,select=2),
    }
    _order="id desc"

    def _check(self,cr,uid,ids):
        for it in self.browse(cr,uid,ids):
            if not it.product_id and not it.container_id:
                return False
            if it.product_id:
                if not it.qty or not it.uom_id:
                    return False
            if it.lot or it.qty or it.uom_id:
                if not it.product_id:
                    return False
        return True

    _constraints=[
        (_check,"Invalid line",[]),
    ]

    def create(self,cr,uid,vals,context={}):
        res=super(in_item,self).create(cr,uid,vals,context)
        wh_id=vals.get("wh_id")
        self.pool.get("avail.item").update_avail(cr,uid,[wh_id])
        return res

    def write(self,cr,uid,ids,vals,context={}):
        res=super(in_item,self).write(cr,uid,ids,vals,context)
        wh_ids=set([])
        for it in self.browse(cr,uid,ids):
            wh_ids.add(it.wh_id.id)
        wh_ids=list(wh_ids)
        self.pool.get("avail.item").update_avail(cr,uid,wh_ids)
        return res

    def unlink(self,cr,uid,ids,context={}):
        wh_ids=set([])
        for it in self.browse(cr,uid,ids):
            wh_ids.add(it.wh_id.id)
        wh_ids=list(wh_ids)
        res=super(in_item,self).unlink(cr,uid,ids,context)
        self.pool.get("avail.item").update_avail(cr,uid,wh_ids)
        return res

    def _dfl_warehouse(self,cr,uid,context):
        user=self.pool.get("res.users").browse(cr,uid,uid)
        emp=user.employee_id
        if not emp:
            res=self.pool.get("warehouse").search(cr,uid,[])
        else:
            res=self.pool.get("warehouse").search(cr,uid,[("department_id","=",emp.department_id.id)])
        if not res:
            return False
        return res[0]

    _defaults={
        "date": lambda *a: time.strftime("%Y-%m-%d"),
        "wh_id": _dfl_warehouse,
    }
in_item()

class out_item(osv.osv):
    _name="out.item"
    _columns={
        "name": fields.char("Running No",size=64,readonly=True),
        "wh_id": fields.many2one("warehouse","Warehouse",required=True,select=1),
        "container_id": fields.many2one("container","Container",select=1),
        "product_id": fields.many2one("product.product","Product",select=1),
        "lot": fields.char("Lot",size=64,select=1),
        "qty": fields.float("Quantity",select=2),
        "uom_id": fields.many2one("product.uom","UoM",select=2),
        "employee_id": fields.many2one("employee","To Employee",required=True,select=2),
        "date": fields.date("Date",required=True,select=2),
        "location_id": fields.many2one("wh.location","Location",required=True,select=2),
    }
    _order="id desc"

    def _check(self,cr,uid,ids):
        for it in self.browse(cr,uid,ids):
            if not it.product_id and not it.container_id:
                return False
            if it.product_id:
                if not it.qty or not it.uom_id:
                    return False
            if it.lot or it.qty or it.uom_id:
                if not it.product_id:
                    return False
        return True

    _constraints=[
        (_check,"Invalid line",[]),
    ]

    def _dfl_warehouse(self,cr,uid,context):
        user=self.pool.get("res.users").browse(cr,uid,uid)
        emp=user.employee_id
        if not emp:
            res=self.pool.get("warehouse").search(cr,uid,[])
        else:
            res=self.pool.get("warehouse").search(cr,uid,[("department_id","=",emp.department_id.id)])
        if not res:
            return False
        return res[0]

    def create(self,cr,uid,vals,context={}):
        res=super(out_item,self).create(cr,uid,vals,context)
        wh_id=vals.get("wh_id")
        self.pool.get("avail.item").update_avail(cr,uid,[wh_id])
        return res

    def write(self,cr,uid,ids,vals,context={}):
        res=super(out_item,self).write(cr,uid,ids,vals,context)
        wh_ids=set([])
        for it in self.browse(cr,uid,ids):
            wh_ids.add(it.wh_id.id)
        wh_ids=list(wh_ids)
        self.pool.get("avail.item").update_avail(cr,uid,wh_ids)
        return res

    def unlink(self,cr,uid,ids,context={}):
        wh_ids=set([])
        for it in self.browse(cr,uid,ids):
            wh_ids.add(it.wh_id.id)
        wh_ids=list(wh_ids)
        res=super(out_item,self).unlink(cr,uid,ids,context)
        self.pool.get("avail.item").update_avail(cr,uid,wh_ids)
        return res

    _defaults={
        "date": lambda *a: time.strftime("%Y-%m-%d"),
        "wh_id": _dfl_warehouse,
    }
out_item()

class int_move(osv.osv):
    _name="int.move"
    _columns={
        "name": fields.char("Running No",size=64,readonly=True),
        "wh_id": fields.many2one("warehouse","Warehouse",required=True,select=1),
        "container_id": fields.many2one("container","Container",select=1),
        "product_id": fields.many2one("product.product","Product",select=1),
        "lot": fields.char("Lot",size=64,select=1),
        "qty": fields.float("Quantity",select=2),
        "uom_id": fields.many2one("product.uom","UoM",select=2),
        "date": fields.date("Date",required=True,select=2),
        "from_location_id": fields.many2one("wh.location","From Location",required=True,select=1),
        "to_location_id": fields.many2one("wh.location","To Location",required=True,select=1),
    }
    _order="id desc"

    def _check(self,cr,uid,ids):
        for it in self.browse(cr,uid,ids):
            if not it.product_id and not it.container_id:
                return False
            if it.product_id and it.container_id:
                return False
            if it.product_id:
                if not it.qty or not it.uom_id:
                    return False
            if it.lot or it.qty or it.uom_id:
                if not it.product_id:
                    return False
        return True

    _constraints=[
        (_check,"Invalid line",[]),
    ]

    def _dfl_warehouse(self,cr,uid,context):
        user=self.pool.get("res.users").browse(cr,uid,uid)
        emp=user.employee_id
        if not emp:
            res=self.pool.get("warehouse").search(cr,uid,[])
        else:
            res=self.pool.get("warehouse").search(cr,uid,[("department_id","=",emp.department_id.id)])
        if not res:
            return False
        return res[0]

    def create(self,cr,uid,vals,context={}):
        res=super(int_move,self).create(cr,uid,vals,context)
        wh_id=vals.get("wh_id")
        self.pool.get("avail.item").update_avail(cr,uid,[wh_id])
        return res

    def write(self,cr,uid,ids,vals,context={}):
        res=super(int_move,self).write(cr,uid,ids,vals,context)
        wh_ids=set([])
        for it in self.browse(cr,uid,ids):
            wh_ids.add(it.wh_id.id)
        wh_ids=list(wh_ids)
        self.pool.get("avail.item").update_avail(cr,uid,wh_ids)
        return res

    def unlink(self,cr,uid,ids,context={}):
        wh_ids=set([])
        for it in self.browse(cr,uid,ids):
            wh_ids.add(it.wh_id.id)
        wh_ids=list(wh_ids)
        res=super(int_move,self).unlink(cr,uid,ids,context)
        self.pool.get("avail.item").update_avail(cr,uid,wh_ids)
        return res

    _defaults={
        "date": lambda *a: time.strftime("%Y-%m-%d"),
        "wh_id": _dfl_warehouse,
    }
int_move()

class avail_item(osv.osv):
    _name="avail.item"
    _columns={
        "name": fields.char("Name",size=64),
        "wh_id": fields.many2one("warehouse","Warehouse",required=True,select=True),
        "container_id": fields.many2one("container","Container",select=True),
        "product_id": fields.many2one("product.product","Product",select=True),
        "lot": fields.char("Lot",size=64,select=True),
        "qty": fields.float("Quantity",required=True,select=2),
        "uom_id": fields.many2one("product.uom","UoM",select=2),
        "location_id": fields.many2one("wh.location","Location",required=True,select=2),
    }
    _order="wh_id,container_id,product_id,lot,uom_id"

    def update_avail(self,cr,uid,wh_ids):
        #print "update_avail"
        t0=time.time()
        for wh in self.pool.get("warehouse").browse(cr,uid,wh_ids):
            ids=self.search(cr,uid,[("wh_id","=",wh.id)])
            self.unlink(cr,uid,ids)

            prod_qtys={}
            for it in wh.in_items:
                if it.container_id:
                    continue
                key=(it.product_id.id,it.lot,it.location_id.id,it.uom_id.id)
                prod_qtys.setdefault(key,0.0)
                prod_qtys[key]+=it.qty
            for it in wh.out_items:
                if it.container_id:
                    continue
                key=(it.product_id.id,it.lot,it.location_id.id,it.uom_id.id)
                prod_qtys.setdefault(key,0.0)
                prod_qtys[key]-=it.qty
            for it in wh.int_moves:
                if it.container_id:
                    continue
                key=(it.product_id.id,it.lot,it.from_location_id.id)
                prod_qtys.setdefault(key,0.0)
                prod_qtys[key]-=it.qty
                key=(it.product_id.id,it.lot,it.to_location_id.id)
                prod_qtys.setdefault(key,0.0)
                prod_qtys[key]+=it.qty
            for (product_id,lot,location_id,uom_id),qty in prod_qtys.items():
                if not qty:
                    continue
                vals={
                    "wh_id": wh.id,
                    "product_id": product_id,
                    "lot": lot,
                    "location_id": location_id,
                    "qty": qty,
                    "uom_id": uom_id,
                }
                self.create(cr,uid,vals)

            cont_qtys={}
            for it in wh.in_items:
                if not it.container_id:
                    continue
                if it.product_id:
                    continue
                key=(it.container_id.id,it.location_id.id)
                cont_qtys.setdefault(key,0)
                cont_qtys[key]+=1
            for it in wh.out_items:
                if not it.container_id:
                    continue
                if it.product_id:
                    continue
                key=(it.container_id.id,it.location_id.id)
                cont_qtys.setdefault(key,0)
                cont_qtys[key]-=1
            for it in wh.int_moves:
                if not it.container_id:
                    continue
                key=(it.container_id.id,it.from_location_id.id)
                cont_qtys.setdefault(key,0)
                cont_qtys[key]-=1
                key=(it.container_id.id,it.to_location_id.id)
                cont_qtys.setdefault(key,0)
                cont_qtys[key]+=1
            for (container_id,location_id),qty in cont_qtys.items():
                if not qty:
                    continue
                cont=self.pool.get("container").browse(cr,uid,container_id)
                if cont.show_prod:
                    for line in cont.content:
                        vals={
                            "wh_id": wh.id,
                            "container_id": container_id,
                            "product_id": line.product_id.id,
                            "lot": line.lot,
                            "location_id": location_id,
                            "qty": qty,
                            "uom_id": line.uom_id.id,
                        }
                        self.create(cr,uid,vals)
                else:
                    vals={
                        "wh_id": wh.id,
                        "container_id": container_id,
                        "location_id": location_id,
                        "qty": qty,
                    }
                    self.create(cr,uid,vals)
        t1=time.time()
        #print "update_avail finished in %.2fs"%(t1-t0)
avail_item()

class container(osv.osv):
    _name="container"
    _columns={
        "name": fields.char("Name",size=64,required=True),
        "content": fields.one2many("content","container_id","Content"),
        "notes": fields.text("Notes"),
        "department_id": fields.many2one("department","Department",required=True),
        "employee_id": fields.many2one("employee","Employee"),
        "date": fields.date("Date",required=True),
        "show_prod": fields.boolean("Show products in warehouse"),
    }
    _defaults={
        "date": lambda *a: time.strftime("%Y-%m-%d"),
    }

    def create(self,cr,uid,vals,context={}):
        if not vals.get("name") or vals.get("name")=="/":
            vals["name"]=self.pool.get('ir.sequence').get(cr,uid,'container')
        return super(container,self).create(cr,uid,vals,context)

    def write(self,cr,uid,ids,vals,context={}):
        res=super(container,self).write(cr,uid,ids,vals,context)
        wh_ids=set([])
        res_=self.pool.get("avail.item").search(cr,uid,[("container_id","in",ids)])
        for it in self.pool.get("avail.item").browse(cr,uid,res_):
            wh_ids.add(it.wh_id.id)
        wh_ids=list(wh_ids)
        self.pool.get("avail.item").update_avail(cr,uid,wh_ids)
        return res
container()

class content(osv.osv):
    _name="content"
    _columns={
        "container_id": fields.many2one("container","Container",required=True,ondelete="cascade"),
        "name": fields.char("Name",size=64),
        "product_id": fields.many2one("product.product","Product",required=True),
        "lot": fields.char("Lot",size=64),
        "qty": fields.float("Quantity",required=True),
        "uom_id": fields.many2one("product.uom","UoM",required=True),
    }
content()

################################
### SHIPPING ###################
################################

class carrier(osv.osv):
    _name="carrier"
    _columns={
        "name": fields.char("Name",size=64,required=True),
    }
carrier()

class shipping(osv.osv):
    _name="shipping"
    _order="date desc"
    _columns={
        "name": fields.char("Running No",size=64,required=True,select=2),
        "ship_type": fields.selection([("in","Incoming"),("out","Outgoing")],"Type of shipping",required=True,select=1),
        "date": fields.date("Date"),
        "state": fields.char("Status",size=64,required=True,readonly=True),
        "requester_id": fields.many2one("employee","Requester",required=True),
        "department_id": fields.many2one("department","Department",required=True,select=1),
        "section_id": fields.many2one("section","Section",required=True),
        "partner_id": fields.many2one("res.partner","Partner",required=True,select=1),
        "pr_id": fields.many2one("purchase.request","Purchase Request"),
        "lines": fields.one2many("shipping.line","ship_id"),

        "container_type": fields.selection([("styro","Styrofoam box"),("box","Box"),("crate","Crate"),("dry","Dry shipper"),("pallet","Pallet")],"Container Type"),
        "temp_type": fields.selection([("dry-ice","Dry Ice"),("room","Room Temp."),('ice-pack','Ice Pack')],"Temperature Control Type"),
        "temp": fields.float("Temperature"),

        "date_shipped": fields.date("Date shipped",select=2),
        "date_arrived": fields.date("Date arrived"),
        "date_released": fields.date("Date released"),
        "date_received": fields.date("Date received",select=2),
        "carrier": fields.many2one("carrier","Carrier",select=1),
        "airbill_no": fields.char("Airway Bill No/Pouch No",size=64,select=2),
        "hawb_no": fields.char("HAWB No",size=64,select=2),

        "notes": fields.text("Notes"),
        "desc": fields.text("Description"),

        "payer_type": fields.selection([("req","Requester"),("dept","Other Department"),("partner","Partner"),("none","None")],"Payer",select=1),
        "payer_dept_id": fields.many2one("department","Other Department"),
        "pay_amount": fields.float("Amount",digits=(16,2)),
        "pay_currency_id": fields.many2one("res.currency","Currency"),
        "pay_project_id": fields.many2one("project","Project",select=1),
        "poc_id": fields.many2one("employee","AFRIMS POC"),
    }

    def _check_airbill(self,cr,uid,ids):
        for obj in self.browse(cr, uid, ids):
            if obj.airbill_no:
                cr.execute("""select id from shipping where airbill_no=%s and id!=%s""",(obj.airbill_no,obj.id))
                res = cr.fetchall()
                if len(res)>=1:
                    return False
        return True

    def _check_hawb(self,cr,uid,ids):
        for obj in self.browse(cr, uid, ids):
            if obj.hawb_no:
                cr.execute("""select id from shipping where hawb_no=%s and id!=%s""",(obj.hawb_no,obj.id))
                res = cr.fetchall()
                if len(res)>=1:
                    return False
        return True

    _constraints = [
        (_check_airbill, 'You can put duplicated Airway Bill no', ['airbill_no']),
        (_check_hawb, 'You can put duplicated HAWB no', ['hawb_no'])
    ]

    _defaults={
        'name': lambda *a: "/",
        "state": lambda *a: "Draft",
        "date": lambda *a: time.strftime("%Y-%m-%d"),
    }

    def create(self,cr,uid,vals,context={}):
        if not vals.get("name") or vals.get("name")=="/":
            vals["name"]=self.pool.get('ir.sequence').get(cr,uid,'shipping')
        return super(shipping,self).create(cr,uid,vals,context)

    def onchange_requester(self,cr,uid,ids,requester_id):
        if not requester_id:
            return {}
        emp=self.pool.get("employee").browse(cr,uid,requester_id)
        vals={
            "department_id": emp.department_id.id,
            "section_id": emp.section_id.id,
        }
        return {"value": vals}

    def copy(self,cr,uid,id,default=None,context={}):
        default.update({
            "name": self.pool.get('ir.sequence').get(cr,uid,'shipping'),
            "state": "Draft",
            'hawb_no':None,
            'airbill_no':None,
        })
        return super(shipping,self).copy(cr,uid,id,default,context)
shipping()

class shipping_line(osv.osv):
    _name="shipping.line"
    _columns={
        "ship_id": fields.many2one("shipping","Shipping"),
        "name": fields.char("Description",size=64,required=True),
        "product_id": fields.many2one("product.product","Product"),
        "qty": fields.float("Quantity",required=True),
        "uom_id": fields.many2one("product.uom","UOM",required=True),
        "weight": fields.float("Weight"),
        "wh_id": fields.many2one("warehouse","Warehouse"),
        "lot": fields.char("Lot",size=64),
        "specimen_type": fields.selection([("non-inf","Non-infectious"),("inf-a","Infectious Cat.A"),("inf-b","Infectious Cat.B")],"Specimen Type"),
    }
shipping_line()

################################
### HR #########################
################################

class employee(osv.osv):
    _name="employee"

    def name_get(self,cr,uid,ids,context={}):
        res=[]
        for emp in self.browse(cr,uid,ids):
            res.append((emp.id,"%s %s"%(emp.fname,emp.lname)))
        return res

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=80):
        if not args:
            args=[]
        if not context:
            context={}
        if name:
            ids = self.search(cr, uid, [('fname', operator, name)] + args, limit=limit, context=context)
            if not ids:
                ids = self.search(cr, uid, [('lname', operator, name)] + args, limit=limit, context=context)
        else:
            ids = self.search(cr, uid, args, limit=limit, context=context)
        return self.name_get(cr, uid, ids, context)

    def _all(self,cr,uid,ids,name,arg,context={}):
        vals_={}
        for emp in self.browse(cr,uid,ids):
            vals={}
            vals["full_name"]=emp.fname+" "+emp.lname
            vals["full_name_prefix"]=emp.prefix+" "+emp.fname+" "+emp.lname
            vals["thai_full_name"]=(emp.thaifname or "")+" "+(emp.thailname or "")
            try:
                vals["age"]=(datetime.datetime.today()-datetime.datetime.strptime(emp.birthdate,"%Y-%m-%d")).days/365
            except:
                vals["age"]=None
            vals["salary_month"]=emp.salary_year/12
            vals["salary_hour"]=emp.salary_year/2080
            vals_[emp.id]=vals
        return vals_

    _columns={
        "users": fields.one2many("res.users","employee_id","Users"),
        "sequence" : fields.integer("Sequence"),
        "lname": fields.char("LName",size=64,required=True,select=True),
        "fname": fields.char("FName/Middle",size=64,required=True,select=True),
        "full_name": fields.function(_all,method=True,type="char",string="Full Name",multi="all"),
        "full_name_prefix": fields.function(_all,method=True,type="char",string="Full Name with Prefix",multi="all"),
        "active": fields.boolean("Active"),
        "rank": fields.char("Special Prefix/Rank",size=64),
        "prefix": fields.selection([("Mr","Mr"),("Mrs","Mrs"),("Ms","Ms"),("Dr","Dr")],"Prefix",required=True),
        "nickname": fields.char("Nickname",size=64),
        "thaifname": fields.char("Thai FName",size=64),
        "thailname": fields.char("Thai LName",size=64),
        "thai_full_name": fields.function(_all,method=True,type="char",string="Thai Full Name",multi="all"),
        "gender2": fields.selection([("M","Male"),("F","Female")],"Gender"),
        "citizenship": fields.many2one("res.country","Citizenship"),
        "birthdate": fields.date("Birthdate"),
        "age": fields.function(_all,method=True,type="integer",string="Age",multi="all"),
        "phone": fields.char("Home Phone",size=64),
        "mobile": fields.char("Mobile Phone",size=64),
        "employee_no": fields.char("Employee#",size=64),
        "ssn_account_no": fields.char("SSN/Account No",size=64),
        "emp_type": fields.selection([("MIL","MIL"),("CA","CA"),("FSN","FSN"),("FSN(PSA)","FSN(PSA)"),("NPSC","NPSC"),("other","Other")],"Type of Employment",select=2),
        "date_ca_emp": fields.date("Date of CA Employment"),
        "date_ca_dep": fields.date("Date of CA Departure"),
        "date_fsn_emp": fields.date("Date of FSN Employment"),
        "date_fsn_dep": fields.date("Date of FSN Departure"),
        "date_fsn_step_inc": fields.date("Date of Step Increase (FSN)"),
        "date_fsn_prom": fields.date("Date of Promotion (FSN)"),
        "grade": fields.char("Grade",size=64),
        "step": fields.char("Step",size=64),
        "salary_year": fields.float("Salary Per Year"),
        "salary_currency": fields.many2one("res.currency","Salary currency"),
        "salary_month": fields.function(_all,method=True,type="float",string="Salary Per Month",multi="all"),
        "salary_hour": fields.function(_all,method=True,type="float",string="Salary Per Hour",multi="all"),
        "title": fields.char("Title",size=64,select=True),
        "position": fields.char("Position (FSN)",size=64),
        "title_short": fields.char("Title(Short)",size=64,select=True),
        "position_series": fields.char("Position Series (FSN)",size=64),
        "supervisor": fields.many2one("employee","Supervisor"),
        "supervisor_ext": fields.char("Supervisor (External)",size=64),
        "rater": fields.many2one("employee","Rater"),
        "rater_ext": fields.char("Rater (External)",size=64),
        "review_official": fields.many2one("employee","Reviewing Official"),
        "review_official_ext": fields.char("Reviewing Official (External)",size=64),
        "site": fields.many2one("site","Site",select=True),
        "section_id": fields.many2one("section","Section",select=True),
        "department_id": fields.many2one("department","Department",select=True,required=True),
        "department_hr": fields.many2one("department","DEPT HR",select=True,required=True),
        "room_no": fields.char("Room",size=64),
        "phone_ext": fields.char("Phone Extension",size=64),
        "email": fields.char("Email",size=64,select=True),
        "email_notif": fields.boolean("Send Email Notif"),
        "high_degree": fields.selection([("Under Bachelor","Under Bachelor"),("Bachelor","Bachelor"),("Master","Master"),("MD","MD"),("Doctorate","Doctorate"),("Postdoc","Postdoc")],"Highest Degree"),
        "mph": fields.boolean("MPH"),
        "postdoc": fields.boolean("Post Doc"),
        "bach_degree": fields.char("Bachelor Degree",size=64),
        "bach_major": fields.char("Bachelor Major",size=64),
        "bach_univ": fields.char("Bachelor University",size=64),
        "bach_country": fields.many2one("res.country","Bachelor Country"),
        "mast_degree": fields.char("Master Degree",size=64),
        "mast_major": fields.char("Master Major",size=64),
        "mast_univ": fields.char("Master University",size=64),
        "mast_country": fields.many2one("res.country","Master Country"),
        "phd_major": fields.char("PhD Major",size=64),
        "phd_univ": fields.char("PhD University",size=64),
        "phd_country": fields.many2one("res.country","PhD Country"),
        "notes": fields.text("Notes"),
        "dl": fields.char("DL",size=64),
        "pass_num": fields.char("Passport Number",size=64),
        "pass_exp_date": fields.date("Passport Expiration Date"),
        "pass_issue_date": fields.date("Passport Date Of Issue"),
        "pass_issue_place": fields.char("Passport Place Of Issue",size=64),
        "pass_name": fields.char("Passport Name",size=64),
        "subrank": fields.selection([("MS","MS"),("MC","MC"),("VC","VC")],"Subrank"),
        "atfp_date": fields.date("AT/FP Date"),
    }
    _order="site,fname"
    _defaults={
        "active": lambda *a: 1,
    }

    def copy(self,cr,uid,id,default=None,context={}):
        if not default:
            default={}
        default.update({
            "users": [],
        })
        return super(employee,self).copy(cr,uid,id,default,context)
employee()

class department(osv.osv):
    _name="department"
    _columns={
        "name": fields.char("Short Name",size=64,required=True),
        "long_name": fields.char("Long Name",size=64),
        "chief_id": fields.many2one("employee","Chief"),
        "address1": fields.char("Address1",size=64),
        "address2": fields.char("Address2",size=64),
        "paragraph": fields.char("Paragraph",size=64),
    }
department()

class section(osv.osv):
    _name="section"
    _columns={
        "name": fields.char("Name",size=64,required=True,select=1),
        "long_name": fields.char("Long Name",size=64,select=1),
        "department_id": fields.many2one("department","Department",required=True,select=1),
        "supervisor_id": fields.many2one("employee","Local Supervisor",select=2,help="Local/Thai Supervisor"),
        "mil_supervisor_id": fields.many2one("employee","Military Supervisor",select=2),
    }

    def name_search(self,cr,uid,name,args=None,operator='ilike',context={},limit=80):
        ids=self.search(cr,uid,[('name',operator,name)])
        if not ids:
            ids=self.search(cr,uid,[('long_name',operator,name)])
        return self.name_get(cr,uid,ids,context)

section()

class res_partner(osv.osv):
    _inherit="res.partner"
    _columns={
        'property_account_payable': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Account Payable",
            method=True,
            view_load=True,
            domain="[('type', '=', 'payable')]",
            help="This account will be used instead of the default one as the payable account for the current partner",
            ),
        'property_account_receivable': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Account Receivable",
            method=True,
            view_load=True,
            domain="[('type', '=', 'receivable')]",
            help="This account will be used instead of the default one as the receivable account for the current partner",
            ),
    }
    _defaults={
        'supplier': lambda *a: 1,
    }

    def name_get(self, cr, uid, ids, context={}):
        if not len(ids):
            return []
        res = [(r['id'], r['ref'] or r['name']) for r in self.read(cr, uid, ids, ['ref','name'], context)]
        return res

    def name_search(self, cr, uid, name, args=None, operator='=ilike', context=None, limit=80):
        if not args:
            args=[]
        if not context:
            context={}
        if name:
            ids_name = self.search(cr, uid, [('name', operator, name)] + args, limit=limit, context=context)
            ids_ref = self.search(cr, uid, [('ref', operator, name)] + args, limit=limit, context=context)
            ids = ids_name + ids_ref
        else:
            ids = self.search(cr, uid, args, limit=limit, context=context)
        return self.name_get(cr, uid, ids, context)

res_partner()

class res_partner_address(osv.osv):
    _inherit="res.partner.address"
    _columns={
        "function": fields.char("Function",size=64),
        "state_id": fields.char("State",size=64),
    }
res_partner_address()
