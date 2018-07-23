##############################################################################
#
#    Copyright (C) 2009-2010 Almacom (Thailand) Ltd.
#    http://almacom.co.th/
#
##############################################################################

from osv import osv,fields
from pprint import pprint

class hq_line_gen(osv.osv_memory):
    _name="hq.line.gen"
    _columns={
        'mode': fields.char("Mode",size=16),
    }
    _defaults={
        'mode' : lambda self,cr,uid,ctx : ctx.get('mode','hq')
    }

    def generate(self,cr,uid,ids,context=None):
        #XXX
        o = self.browse(cr,uid,ids)[0]
        print 'generate'
        print 'mode',o.mode
        mode = o.mode

        cr.execute("""delete from hq_statement_line
        where hq_id in (select id from hq_statement where mode=%s )""",(o.mode,))

        cause=["mode=%s","hq_statement.e_state not in ('Draft','Canceled')"]
        value=[mode]

        if mode=="hq":
            cause=["reconcile_ok=True"]

        cr.execute("""
            SELECT id, e_sites,e_desc,"desc", fy_id, type,e_type, e_requester,
                                                            e_supplier,
                                                            e_product,
                                                            name,
                                                            e_name,
                                                            eor,
                                                            e_eor,
                                                            purchase_no,
                                                            e_purchase_no,
                                                            voucher_no,
                                                            amount,
                                                            e_amount,
                                                            apc,
                                                            e_apc
            FROM hq_statement
            WHERE %s """ % ' and '.join(cause) ,value)
        res = cr.dictfetchall()
        for  r in res:
            #amount = mode=='hq' and r['amount'] or r['e_amount']
            if mode=='hq':
                amount = r['amount'] or 0.0
            else:
                amount = r['e_amount'] or 0.0

            type = mode=='hq' and r['type'] or r['e_type']

            hq = self.pool.get("hq.statement").browse(cr,uid,r['id'])
            print "*"*30
            print hq.tdy_id,hq.prl_id

            apc = mode=='hq' and r['apc'] or r['e_apc']
            eor = mode=='hq' and r['eor'] or r['e_eor']
            name = mode=='hq' and r['name'] or r['e_name']
            purchase_no = mode=='hq' and r['purchase_no'] or r['e_purchase_no']
            voucher_no = mode=='hq' and r['voucher_no'] or ''

            site_group={}
            projects = []
            prl = hq.prl_id
            tdy = hq.tdy_id
            vals={
                "hq_id": r['id'],
                "prl_id" : prl.id,
                "tdy_id" : tdy.id,
                "site": r['e_sites'], #TODO:
                "desc" : r["e_desc"],
                "e_product" : r["e_desc"],
                "fy_id" : r["fy_id"],
                "type" : type,
                "mode": mode,
                "e_requester" : r["e_requester"],
                "e_supplier" : r["e_supplier"],

                "name" : name,

                "purchase_no" : purchase_no,
                "voucher_no" : voucher_no,

                "amount": amount,
                "apc":apc,
                "eor":eor,
                }
            obj_projects=[]
            if tdy:
                print 'tdy',hq.tdy_id.name
                obj_projects = hq.tdy_id.projects
            elif prl:
                print 'prl',prl.name
                obj_projects = hq.prl_id.projects


            for project in obj_projects:
                site_group.setdefault(project.site_id,0.0)
                ratio = project.percent/100.0

                site_group[project.site_id] += project.percent

                vals['project_code']=project.project_id.name
                vals['project_amount']=amount*ratio

                l_id = self.pool.get('hq.statement.line').create(cr,uid,vals)

            #for site,percent in site_group.items():
                #print 'site',site,percent
            #pprint(r)
            #print vals

        return  {'type': 'ir.actions.act_window_close'}
hq_line_gen()
