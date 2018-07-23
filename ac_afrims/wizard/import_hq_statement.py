##############################################################################
#
#    Copyright (C) 2009-2010 Almacom (Thailand) Ltd.
#    http://almacom.co.th/
#
##############################################################################

from osv import osv,fields
import cStringIO as StringIO
import csv
import base64
from pprint import pprint
from mx import DateTime

class import_hq_statement(osv.osv_memory):
    _name="import.hq.statement"

    _columns = {
        'data': fields.binary('File'),
        'note':fields.text('Notes',readonly=1),
        'state':fields.selection([('draft','Draft'),('done','Done')],'State',readonly=1),
    }

    _defaults={
        'state':lambda *a:'draft'
    }

    def do_clear(self, cr, uid, ids, context):
        cr.execute("truncate table hq_statement cascade")
        return True

    def do_import(self, cr, uid, ids, context):
        """
            ** Main task is data convert from csv to ERP
        """
        #cr.execute(""" delete from hq_statement """)

        apc_obj = self.pool.get('apc')
        apc_category_obj = self.pool.get('apc.category')
        fy_obj = self.pool.get('apc.fiscalyear')

        import_data = self.browse(cr, uid, ids)[0]
        data = base64.decodestring(import_data.data)

        rd=csv.DictReader(StringIO.StringIO(data))

        #headers=[
            #'purno','reqno','fiscalyear','apc',
            #'category','project','site','pritemno',
            #'pritemdesc','quantity','entrydate','purstatus',
            #'budgetstatus','voucherno','completedate','lname',
            #'fname','mi','eor','budgetcommit','ponumber',
            #'vendorcode', 'vendorname','routename','prtypedesc',
            #'prtype'
        #]

        total_record= imported_record=skipped_record=updated_record= 0
        no_apc=[]

        for l in rd:
            #new column not support
            if l.get('Expr1',False) and not l.get('apc',False):
                l['apc']=l['Expr1'].strip()

            total_record+=1

            name = l['reqno']
            pr_no=l['purno']
            date = False
            date_done = False
            #convert date format
            if l['entrydate']:
                date= DateTime.strptime(l['entrydate'],"%d-%b-%y")
            if l['completedate']:
                date_done=DateTime.strptime(l['completedate'],"%d-%b-%y")

            #import pdb;pdb.set_trace()
            seq=l['pritemno']
            desc=l['pritemdesc'] or l['fname']
            type=l['prtype']
            project=l['project']

            # find and set fiscalyear
            fy_id=False
            fy_id = fy_obj.search(cr,uid,[('name','=',l['fiscalyear'])])
            if not fy_id:
                fy_id = fy_obj.search(cr,uid,[('name','=',l['fiscalyear']),('active','=',False)])
            # set category
            category = l['category']=='UMASS' and 'VIRO' or l['category']
            apc_category_id = apc_category_obj.search(cr,uid,[('name','=',category)]) or False

            #XXX : want to skip or not
            if not apc_category_id:
                skipped_record+=1
                continue

            # set APC
            apc_id=False
            apc_id= apc_obj.search(cr,uid,[
                ('code','=',l['apc']),
                ('fiscalyear_id','in',fy_id),
                ('category_id','in',apc_category_id)
                ])
            if not apc_id:
                apc_id= apc_obj.search(cr,uid,[
                ('code','=',l['apc']),
                ('category_id','in',apc_category_id),
                ('fiscalyear_id','in',fy_id),
                ('active','=',False)
                ])
            if not apc_id:
                #print 'no apc',l['apc']
                #print l
                skipped_record+=1
                no_apc.append(l['apc'])
                continue

            site=l['site']
            eor=l['eor']

            pc_state=l['purstatus'].capitalize()
            bg_state=l['budgetstatus']

            purchase_no=l['ponumber'].strip().replace('"','').replace("'",'') or False
            voucher_no=l['voucherno'].strip().replace('"','').replace("'",'') or False
            amount=l['budgetcommit']
            partner_name=l['vendorname']
            partner_ref=l['vendorcode']
            lname=l['lname'].strip()
            fname=l['fname'].strip()
            mname=l['mi'].strip()

            staff_name = lname+ (fname and (" "+fname) or '') + (mname and (" "+ mname) or '' )

            vals = {
                "name":name,
                "pr_no":pr_no,
                "date":date,
                "date_done":date_done,
                "seq":seq,
                "desc":desc,
                "type":type,
                "project":project,

                "apc_id":apc_id[0],
                "apc" : l['apc'],
                "apc_category_id":apc_category_id[0],
                "fy_id":fy_id[0],

                "site":site,
                "eor":eor,
                "pc_state":pc_state,
                "bg_state":bg_state,
                "purchase_no":purchase_no,
                "voucher_no":voucher_no,
                "amount":amount,
                "partner_name":partner_name,
                "partner_ref":partner_ref,
                'staff_name':staff_name,
            }


            #check existing record
            cr.execute('''select id from hq_statement where name=%s and seq=%s
            ''',(name,seq,))
            res = cr.fetchall()
            if res:
                #update existing recored
                existing_id = map(lambda x:x[0],res)
                self.pool.get('hq.statement').write(cr,uid,existing_id,vals)
                #print "Record already exist no need to import"
                updated_record+=1
            # if record not exist : create
            else:
                self.pool.get('hq.statement').create(cr,uid,vals)
                imported_record+=1
            #print 'create : ',st_id
        note ='Total Record: %i records\n'%total_record
        note += "Imported : %i Records\n" % imported_record
        note += "Skipped : %i Records\n" % skipped_record
        note += "Update : %i Records\n" % updated_record
        if no_apc:
            no_apc = list(set(no_apc))
            note+=" Missing APC : %s" % ','.join(no_apc)
        return self.write(cr,uid,ids,{'state':'done','note':note})

    def btn_done(self, cr, uid, ids, context):
        return  {'type': 'ir.actions.act_window_close'}

    def generate(self,cr,uid,context=None):
        return  {'type': 'ir.actions.act_window_close'}
import_hq_statement()

