##############################################################################
#
#    Copyright (C) 2009-2010 Almacom (Thailand) Ltd.
#    http://almacom.co.th/
#
##############################################################################

from osv import osv,fields

def _tdy_category_get(self, cr, uid, context={}):
    cr.execute('select name, name from tdy_categ where active=True')
    return cr.fetchall()

def _requester_get(self, cr, uid, context={}):
    cr.execute('select fname||\' \'||lname ,fname||\' \'||lname  from employee order by fname')
    return cr.fetchall()

def _pr_type(self, cr, uid, context={}):
    cr.execute('select name,name from pr_type where  active=True order by name')
    res = cr.fetchall()
    res.append(('TDY','TDY',))
    return res

def _section_get(self, cr, uid, context={}):
    cr.execute('select name,name from section')
    return cr.fetchall()

######################
##### IMPORT ######
######################
class hq_statement(osv.osv):
    _name="hq.statement"
    _order="date,name,seq"


    def _projects(self,cr,uid,ids,name,arg,context={}):
        res={}
        for record in self.browse(cr,uid,ids):
            #split project name
            names=(record.project or '').split(',')
            #strip to remove white space
            names=[n.strip() for n in names]
            cr.execute('''select id from project where name in %s''',(tuple(names),))
            result =cr.fetchall()
            res[record.id]=map(lambda x:x[0],result)
        return res

    def _sites(self,cr,uid,ids,name,arg,context={}):
        res={}
        for record in self.browse(cr,uid,ids):
            #split site name
            names=(record.site or '').split(',')
            #strip to remove white space
            names=[n.strip() for n in names]
            cr.execute('''select id from site where name in %s''',(tuple(names),))
            result =cr.fetchall()
            res[record.id]=map(lambda x:x[0],result)
        return res

    def _partner(self,cr,uid,ids,name,arg,context={}):
        res={}
        for record in self.browse(cr,uid,ids):
            res[record.id]=False
        return res

    def _eor(self,cr,uid,ids,name,arg,context={}):
        res={}
        for record in self.browse(cr,uid,ids):
            eor_id=False
            name=(record.eor or '').strip()
            cr.execute('''select id from eor where code = %s''',(name,))
            result =cr.fetchall()
            #print "result",result
            if result:
                eor_id =map(lambda x:x[0],result)[0]

            res[record.id]=eor_id
        return res

    def _related_datas(self,cr,uid,ids,name,arg,context={}):
        res={}
        for record in self.browse(cr,uid,ids):
            doc_no=record.name
            po_no = record.purchase_no

            prl_id=record.prl_id
            prl_ids=[]

            tdy_id=record.tdy_id
            tdy_ids=[]

            if not record.reconcile_ok:
                if record.type=='TDY':
                    if not tdy_id:
                        tdy_ids = self.pool.get('tdy.request').search(cr,uid,[('po_no','=',po_no),('fy_id','=',record.fy_id.id)])
                    if not tdy_ids:
                        tdy_ids = self.pool.get('tdy.request').search(cr,uid,[('doc_no','=',doc_no),('fy_id','=',record.fy_id.id)])
                else:
                    if not prl_id:
                        prl_ids = self.pool.get('purchase.request.line').search(cr,uid,[('pr_id.doc_no','=',doc_no),('fy_id','=',record.fy_id.id)])
            res[record.id]= {
                'prl_ids':prl_ids,
                'tdy_ids': tdy_ids,
                }
        return res

    def _get_prl(self,cr,uid,id,context=None):

        record = self.browse(cr,uid,id)
        prl_id=False

        if record.mode=='hq':
            if record.type!='TDY':
                doc_no = record.name
                sequence= record.seq

                cause=[' o.doc_no=%s ',' fy_id=%s ']
                value=[doc_no,record.fy_id.id]

                if record.type not in ('BPA','MISC'):
                    cause+=['l.sequence=%s']
                    value+=[sequence]

                #search using document no+sequence
                cr.execute('''
                    SELECT l.id
                    FROM purchase_request_line l ,
                         purchase_request o
                    WHERE o.id = l.pr_id
                      AND o.department_id=1
                      AND %s
                    order by l.sequence ''' % ' and '.join(cause) , value )

                result = map(lambda x:x[0], cr.fetchall())
                prl_id= result and result[0] or False
        # if local data
        else:
            prl_id = record.manual_prl_id and  record.manual_prl_id.id or False


        return prl_id

    def _get_pr(self,cr,uid,id,context=None):
        if not id:
            return False

        cr.execute('''
            SELECT pr_id
            FROM purchase_request_line
            where id=%s
            ''',(id,))

        result = cr.fetchone()

        pr_id= result and result[0] or False

        return pr_id

    def _get_tdy(self,cr,uid,id,context={}):
        record =self.browse(cr,uid,id)
        tdy_id = False

        if record.mode=='hq':
            if record.type=='TDY':

                doc_no = record.name or ''
                po_no = record.purchase_no or ''
                fy_id = record.fy_id.id
                cr.execute('''select id from tdy_request \
                                where ( doc_no=%s or po_no=%s ) and fy_id=%s
                                and department_id=1 ''',(doc_no,po_no,fy_id,))
                result = map(lambda x:x[0], cr.fetchall())

                if not result:
                    doc_no=doc_no.replace('AF','AF-')
                    cr.execute('''select id from tdy_request \
                                    where (doc_no = %s or po_no=%s ) and fy_id=%s''',(doc_no,doc_no,fy_id,))
                    result = map(lambda x:x[0], cr.fetchall())

                tdy_id= result and result[0] or False
        else:
            tdy_id = record.manual_tdy_id and record.manual_tdy_id.id or False

        return tdy_id

    def _get_data(self,cr,uid,ids,name,arg,context={}):
        res={}
        for record in self.browse(cr,uid,ids):
            prl_id=self._get_prl(cr,uid,record.id)
            tdy_id=self._get_tdy(cr,uid,record.id)
            pr_id=self._get_pr(cr,uid,prl_id)
            res[record.id]={
                'prl_id' : prl_id,
                'tdy_id' : tdy_id,
                'reconcile_ok' : (prl_id or tdy_id) and True or False,
                'pr_id': pr_id,
            }
            #print (prl_id or tdy_id) and True or False ,prl_id ,pr_id,tdy_id
        return res

    def _get_local_datas(self,cr,uid,ids,name,arg,context={}):
        res={}
        for record in self.browse(cr,uid,ids):
            amount = record.amount
            e_name=e_doc_no=e_seq= e_desc=e_tdy_location= e_eor= e_purchase_no=invoice_ref=False
            e_requester=e_section=e_supplier=e_product= e_state=e_currency_id=False
            e_tdy_range=e_tdy_category=False
            e_type=e_apc=e_apc_category=False
            e_product_qty=e_price_unit=0.0
            e_uom_id=False
            e_date =False
            e_amount=0.0
            e_sites=''
            e_projects=False

            if record.reconcile_ok:
                prl = record.prl_id
                tdy=record.tdy_id
                pr=False
                if prl:

                    pr = prl.pr_id
                    e_name=pr.name
                    e_date=pr.date
                    e_doc_no=pr.doc_no
                    e_seq= prl.sequence
                    e_desc=prl.name
                    #e_eor=prl.eor_id.name_get()[0][1]
                    e_eor= prl.eor_id and  prl.eor_id.name_get()[0][1] or False
                    e_purchase_no=pr.po_no
                    e_type=pr.type
                    invoice_ref=pr.invoice_ref

                    e_amount=prl.subtotal
                    e_requester=pr.requester_id.name_get()[0][1]
                    e_section=pr.requester_id.section_id.name
                    e_supplier=pr.supplier_id and pr.supplier_id.name_get()[0][1] or False
                    e_product=prl.product_id and prl.product_id.name_get()[0][1] or False
                    #e_state='draft'
                    e_state=pr.state    # <<< Weng edit
                    e_currency_id=pr.currency_id.id

                    e_product_qty = prl.qty
                    e_price_unit= prl.price_unit
                    e_uom_id = prl.uom_id.id

                    for apc in pr.apcs:
                        e_apc=apc.apc_id.name_get()[0][1]
                        e_apc_category=apc.apc_id.category_id.name_get()[0][1]

                    site_group={}
                    projects = []
                    sites=[]
                    for project in prl.projects:
                        site_group.setdefault(project.site_id,0.0)

                        ratio = project.percent/100.0

                        projects.append( '%s(%s%%:%s)'%(project.project_id.name,project.percent,amount*ratio) )

                        #e_projects+= '%s(%s%%:%s)' %(project.project_id.name,project.percent,amount*ratio)

                        site_group[project.site_id] += project.percent

                    for site,percent in site_group.items():
                        sites.append( '%s(%s%%)'%(site,percent) )

                    e_projects = ','.join(projects)
                    e_sites = ','.join(sites)
                elif tdy:
                    e_amount = tdy.cost_total
                    e_type='TDY'
                    e_name=tdy.name
                    e_doc_no=tdy.doc_no
                    e_date =tdy.dep_date
                    e_desc=tdy.purpose
                    e_tdy_location = tdy.tdy_location.name

                    travel_ok = record.eor=='21T1' and True or False

                    e_eor= travel_ok and tdy.travel_eor_id.name_get()[0][1] or tdy.per_diem_eor_id.name_get()[0][1]

                    e_purchase_no=tdy.po_no
                    e_state=tdy.state
                    e_tdy_range=tdy.range
                    e_tdy_category=tdy.categ_id.name_get()[0][1]

                    e_requester=tdy.requester_id.name_get()[0][1]
                    e_section=tdy.requester_id.section_id.name

                    site_group={}
                    projects = []
                    for project in tdy.projects:
                        site_group.setdefault(project.site_id,0.0)
                        ratio = project.percent/100.0

                        projects.append( '%s(%s%%:%s)'%(project.project_id.name,project.percent,amount*ratio) )

                        site_group[project.site_id] += project.percent

                    e_projects = ','.join(projects)

                    sites=[]
                    for site,percent in site_group.items():
                        if not site:
                            site='XXX',
                        sites.append( '%s(%s%%)'%(site,percent) )

                    e_sites = ','.join(sites)

                    for apc in tdy.apcs:
                        e_apc=apc.apc_id.name_get()[0][1]
                        e_apc_category=apc.apc_id.category_id.name_get()[0][1]

            vals={
                'e_name':e_name,
                'e_date':e_date,
                'e_type':e_type,
                'e_doc_no':e_doc_no,
                'e_seq':e_seq,
                'e_projects':e_projects,
                'e_sites':e_sites,
                'e_desc':e_desc and e_desc[0:1024] or '',
                'e_tdy_location':e_tdy_location,
                'e_eor':e_eor,
                'e_purchase_no':e_purchase_no,
                'invoice_ref':invoice_ref,
                'e_amount':e_amount,
                'e_requester':e_requester,
                'e_supplier':e_supplier,
                'e_product':e_product,
                'e_state':e_state,
                'e_currency_id':e_currency_id,
                'e_section':e_section,
                'e_tdy_range':e_tdy_range,
                'e_tdy_category':e_tdy_category,
                'e_apc':e_apc,
                'e_apc_category':e_apc_category,
                'e_product_qty': e_product_qty,
                'e_price_unit': e_price_unit,
                'e_uom_id': e_uom_id,
            }
            res[record.id]=vals
        return res

    _STORE_DATA ={
                'hq.statement' : (lambda self,cr,uid,ids,context={}:ids,
                ['prl_id','tdy_id','purchase_no','amount','mode'],50)
    }

    _STORE_MAIN={
        'hq.statement' : (lambda self,cr,uid,ids,context={}:ids,
            ['name','type','mode'
            ,'seq','manual_prl_id'
            ,'manual_tdy_id'
            ,'purchase_no','fy_id'],10)
    }

    _columns={
        'mode': fields.selection([('hq','HQ'),('local','Local')],'Mode',required=1,select=1),
        'name':fields.char('Doc #(HQ)',size=128,help="reqno",readonly=1,select=1),# = doc_no
        'pr_no':fields.char('Running No',size=32,help="Running No.",readonly=1,select=1),
        'date':fields.date('Date(HQ)',help='entrydate',readonly=1,select=1),
        'date_done':fields.date('Completed Date(HQ)',help='completedate',readonly=1),
        'seq': fields.integer('Seq(HQ)',help='pritemno',readonly=1,select=1),
        'desc': fields.char('Desc(HQ)',size=256,help='pritemdesc',readonly=1,select=1),
        'type':fields.selection([
            ('BPA','BPA'),
            ('CARD','CARD'),
            ('CASH','CASH'),
            ('CHBK','CHBK'),
            ('CONT','CONT'),
            ('EFT','EFT'),
            ('IDIQ','IDIQ'),
            ('MISC','MISC'),
            ('PR','PR'),
            ('REQ','REQ'),
            ('TDY','TDY'),
                ],'PR Type(HQ)',help='prtype',readonly=1,select=1), #no selection
        'project':fields.char('Proj(HQ)',size=1028,help='project',readonly=1,select=1),
        'project_ids':fields.function(_projects,method=True,type='many2many',relation='project',string='Proj'),

        'apc':fields.char('APC(HQ)',size=64,readonly=1,select=1),
        'apc_id':fields.many2one('apc','APC(HQ)',help='apc',readonly=1,select=1),
        'apc_category_id':fields.many2one('apc.category','Category(HQ)',help='category',readonly=1,select=1),

        'fy_id':fields.many2one('apc.fiscalyear','Fiscal Year',help='fiscalyear',readonly=1,select=1),
        'site':fields.char('Site(HQ)',size=256,help='site',readonly=1,select=1),
        'site_ids':fields.function(_sites,method=True,type='many2many',relation='site',string='Sites'),

        'eor':fields.char('EOR(HQ)',size=32,help='eor',readonly=1,select=1),
        #TODO: e_eor after #selection
        'eor_id':fields.function(_eor,method=True,type='many2one',relation='eor',string='EOR'),
        'pc_state':fields.selection([('W','W'),('Y','Y'),('N','N'),('R','R'),('A','A'),('C','C'),('X','X')],'Purchase Status',help='purstatus',readonly=1,select=2),
        'bg_state':fields.selection([('C','C'),('N','N'),('Y','Y'),('P','P')],'Budget Status',help='budgetstatus',readonly=1,select=2),
        #'tc'
        'purchase_no':fields.char('PO #(HQ)',size=32,help='ponumber',readonly=1,select=1),
        'voucher_no':fields.char('Voucher #(HQ)',size=32,help='voucherno',readonly=1,select=1),
        'amount': fields.float('Amt(HQ)',digits=(16,2),help='budgetcommit',readonly=1,select=2),
        'partner_name':fields.char('Supplier Name',size=256,help='vendorname',readonly=1),
        'partner_ref':fields.char('Supplier Code',size=32,help="vendorcode",readonly=1),
        'partner_id':fields.function(_partner,method=True,type='many2one',relation='res.partner',string='Supplier'),
        'prl_id':fields.function(_get_data,method=True,type='many2one',relation='purchase.request.line',string='Purchase Request',
            store=_STORE_MAIN,multi="main"
            ),
        'tdy_id':fields.function(_get_data,method=True,type='many2one',relation='tdy.request',string='TDY',
            store=_STORE_MAIN,multi="main"),
        'reconcile_ok':fields.function(_get_data,method=True,type='boolean',string='Reconciled',help='OK: this entry match with HQ data',
            store=_STORE_MAIN,multi="main",select=1
        ),

        'manual_prl_id':fields.many2one('purchase.request.line','Manual PR line',help='Manually Select Request line'),
        'manual_tdy_id':fields.many2one('tdy.request','Manual TDY',help='Manually select TDY'),
        'pr_id': fields.function(_get_data,method=True,type="many2one",relation='purchase.request',string='PR',
            multi="main",
            store=_STORE_MAIN),

        'prl_ids':fields.function(_related_datas,method=True,type='many2many',relation='purchase.request.line',string='Similar PR',multi="data"),
        'tdy_ids':fields.function(_related_datas,method=True,type='many2many',relation='tdy.request',string='Similar TDY',multi="data"),

        'staff_name':fields.char('Staff Name',size=256,help='lname,fname,mi',readonly=1),

        #data read from erp
        'e_name': fields.function(_get_local_datas,method=True,type='char',size=256,string='Running No(E)',multi='local',
            store=_STORE_DATA,select=2),
        'e_date': fields.function(_get_local_datas,method=True,type='date',string='Departure Date',multi='local',
            store=_STORE_DATA),
        'e_type': fields.function(_get_local_datas,method=True,type='selection',size=32,string='PR Type(E)',multi='local',
            store=_STORE_DATA,
            selection=_pr_type,select=2),
        'e_seq': fields.function(_get_local_datas,method=True,type='integer',string='Seq(E)',multi='local',
            store=_STORE_DATA),
        'e_doc_no': fields.function(_get_local_datas,method=True,type='char',size=256,string='Doc #(E)',multi='local',
            store=_STORE_DATA,select=2),#test step update
        'e_projects': fields.function(_get_local_datas,method=True,type='char',size=1024,string='Proj(E)',multi='local',
            store=_STORE_DATA),
        'e_sites': fields.function(_get_local_datas,method=True,type='char',size=256,string='Sites(E)',multi='local',
            store=_STORE_DATA),
        'e_desc': fields.function(_get_local_datas,method=True,type='char',size=1024,string='Desc(e)',multi='local',
            store=_STORE_DATA,select=2),
        'e_tdy_location': fields.function(_get_local_datas,method=True,type='char',size=1024,string='TDY Location(e)',multi='local',
            store=_STORE_DATA),
        'e_purchase_no': fields.function(_get_local_datas,method=True,type='char',size=256,string='PO #(E)',multi='local',
            store=_STORE_DATA),
        'e_amount': fields.function(_get_local_datas,method=True,type='float',digits=(16,2),string='Amt(E)',multi='local',
            store=_STORE_DATA),
        'e_requester': fields.function(_get_local_datas,method=True,type='selection',
            selection=_requester_get,
            size=256,string='Requester',multi='local',
            store=_STORE_DATA,select=2),
        'e_section': fields.function(_get_local_datas,method=True,type='selection',
            selection=_section_get,
            size=64,string='Section',multi='local',
            store=_STORE_DATA),
        'e_state': fields.function(_get_local_datas,method=True,type='char',size=256,string='PR Status(E)',multi='local',
            store=_STORE_DATA),
        'e_tdy_range': fields.function(_get_local_datas,method=True,type='selection',
            selection=[("local","Local"),("inter","International")],
            size=256,string='TDY Range(E)',multi='local',
            store=_STORE_DATA),

        'e_apc': fields.function(_get_local_datas,method=True,type='char',size=256,string='APC(E)',multi='local',
            store=_STORE_DATA,select=2),

        'e_apc_category': fields.function(_get_local_datas,method=True,type='char',size=256,string='APC Category(E)',multi='local',
            store=_STORE_DATA),
        'e_supplier': fields.function(_get_local_datas,method=True,type='char',size=256,string='Supplier(E)',multi='local',
            store=_STORE_DATA),
        'e_product': fields.function(_get_local_datas,method=True,type='char',size=256,string='Product(E)',multi='local',
            store=_STORE_DATA),
        'e_eor': fields.function(_get_local_datas,method=True,type='char',size=256,string='EOR(E)',multi='local',
            store=_STORE_DATA,select=2),
        'e_tdy_category': fields.function(_get_local_datas,method=True,type='selection'\
            ,selection=_tdy_category_get
            ,size=256,string='TDY Category(E)',multi='local',
            store=_STORE_DATA),

        'e_currency_id': fields.function(_get_local_datas,method=True,type='many2one',relation='res.currency',string='Currency(E)',multi='local',
            store=_STORE_DATA),

        'invoice_ref': fields.function(_get_local_datas,method=True,type='char',size=256,string='Inv #(E)',multi='local',
            store=_STORE_DATA),

        'e_product_qty': fields.function(_get_local_datas,method=True,type='float',digits=(16,2),string='QTY(E)',multi='local',
            store=_STORE_DATA),
        'e_price_unit': fields.function(_get_local_datas,method=True,type='float',digits=(16,2),string='Unit Price(E)',multi='local',
            store=_STORE_DATA),
        'e_uom_id': fields.function(_get_local_datas,method=True,type="many2one" ,relation="product.uom", string='UoM(E)',multi='local',
            store=_STORE_DATA),
        #travel_range, tdy category
    }
    _defaults={
        'mode':lambda *a : 'hq',
    }
hq_statement()

#for view

class hq_statement_hq_pr(osv.osv):
    _name="hq.statement.hq.pr"
    _inherit="hq.statement"
    _table="hq_statement"
hq_statement_hq_pr()

class hq_statement_hq_tdy(osv.osv):
    _name="hq.statement.hq.tdy"
    _inherit="hq.statement"
    _table="hq_statement"
hq_statement_hq_tdy()

class hq_statement_e_pr(osv.osv):
    _name="hq.statement.e.pr"
    _inherit="hq.statement"
    _table="hq_statement"
hq_statement_e_pr()

class hq_statement_e_tdy(osv.osv):
    _name="hq.statement.e.tdy"
    _inherit="hq.statement"
    _table="hq_statement"
hq_statement_e_tdy()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4
