##############################################################################
#
#    Copyright (C) 2009-2010 Almacom (Thailand) Ltd.
#    http://almacom.co.th/
#
##############################################################################

from osv import osv,fields
from pprint import pprint
import time

class e_statement_gen(osv.osv_memory):
    _name="e.statement.gen"
    _columns={
        'fy_id':fields.many2one('apc.fiscalyear','Fiscal Year',required=1),
    }

    def generate_pr(self,cr,uid,ids,context=None):
        wiz = self.browse(cr,uid,ids)[0]
        fy_id = wiz.fy_id.id
        hq_obj = self.pool.get('hq.statement')

        # search PR line which not match with HQ
        # Using active status ( no draft/cancel )

        # PR Line
        cr.execute("""
            select l.id,o.type,o.date
                from purchase_request_line l,purchase_request o
            where l.pr_id=o.id
                and o.state not in ('Draft','Canceled')
                and l.fy_id=%s
                and l.eor_id is not null
                and o.id not in (select pr_id from hq_statement where pr_id is not null and mode='hq' )
            order by o.date,l.id
        """,(fy_id,))

        for r in cr.dictfetchall():
            print 'PR', r
            # check existing statement for update/create
            hq_id = hq_obj.search(cr,uid,[('manual_prl_id','=',r['id'])])

            vals={
                    'mode':'local',
                    'e_type':r['type'],
                    'type':"PR",
                    'manual_prl_id':r['id'],
                    'e_date':r['date'],
                    'fy_id': fy_id,
            }
            # create new record
            if not hq_id:
                #search existing PR/TDY in statement
                a = time.time()

                hq_obj.create(cr,uid,vals)
                b = time.time()

            else: # Exist just update
                hq_obj.write(cr,uid,hq_id,vals)

        return True

    def generate_tdy(self,cr,uid,ids,context=None):
        wiz = self.browse(cr,uid,ids)[0]
        fy_id = wiz.fy_id.id
        hq_obj = self.pool.get('hq.statement')

        cr.execute("""
            select
            o.id,o.date
            from tdy_request o
            where o.state not in ('Draft','Canceled')
                and o.fy_id=%s
                and o.id not in (select tdy_id from hq_statement where ( tdy_id is not null or manual_tdy_id is not null) and mode='hq' )
            order by o.date,o.id
        """,(fy_id,))
        print 'tdy...', cr._obj.query

        for r in cr.dictfetchall():
            print 'tdy',r
            hq_id = hq_obj.search(cr,uid,[('manual_tdy_id','=',r['id'])])

            vals={
                    'mode':'local',
                    'e_type':'TDY',
                    'type':"TDY",
                    'manual_tdy_id':r['id'],
                    'e_date':r['date'],
                    'fy_id': fy_id,
            }

            if not hq_id:
                #search existing PR/TDY in statement
                a = time.time()

                hq_obj.create(cr,uid,vals)
                b = time.time()

            else:
                hq_obj.write(cr,uid,hq_id,vals)
        return True

    def generate(self,cr,uid,ids,context=None):
        wiz = self.browse(cr,uid,ids)[0]
        fy_id = wiz.fy_id.id
        hq_obj = self.pool.get('hq.statement')

        self.generate_pr(cr,uid,ids,context=context)
        self.generate_tdy(cr,uid,ids,context=context)

        return  {'type': 'ir.actions.act_window_close'}

    def do_clear(self, cr, uid, ids, context):
        cr.execute(""" delete from hq_statement where mode='local' """)
        cr.commit()
        return True

e_statement_gen()
