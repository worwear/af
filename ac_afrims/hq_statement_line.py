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
from mx import DateTime

class hq_statement_line(osv.osv):
    _name="hq.statement.line"

    _columns ={

        'hq_id':fields.many2one('hq.statement','HQ',ondelete="cascade"),
        'prl_id':fields.many2one('purchase.request.line',string='Purchase Request'),
        'tdy_id':fields.many2one('tdy.request',string='TDY'),

        'project_code':fields.char('Proj(E)',size=64,readonly=1),
        'project_amount':fields.float('Proj. Amt',digits=(16,2),readonly=1),

        'site':fields.char('Site(E)',size=256,help='site',readonly=1),

        'desc': fields.char('Item Desc(E)',size=256,help='pritemdesc',readonly=1),
        'fy_id':fields.many2one('apc.fiscalyear','Fiscal Year',help='fiscalyear',readonly=1),

        'type':fields.char("PR Type",size=16),
        #TODO : e_pr_type # TDY=tdy, PR ( pr.type)

        'e_requester': fields.char('Requester',size=256,readonly=1),
        'e_supplier': fields.char('Supplier(E)',size=256,readonly=1),
        'e_product': fields.char(string='Product(E)',size=256,readonly=1),

        'name':fields.char('Doc #',size=128,help="reqno",readonly=1),
        'seq': fields.integer('Seq',help='pritemno',readonly=1),
        'eor':fields.char('EOR',size=32,help='eor',readonly=1),
        'mode':fields.char('Mode',size=32,readonly=1),
        'purchase_no':fields.char('PO #(HQ)',size=32,help='ponumber',readonly=1),
        'voucher_no':fields.char('Voucher #(HQ)',size=32,help='voucherno',readonly=1),
        'amount': fields.float('Amt',digits=(16,2),help='budgetcommit',readonly=1),
        'apc_id':fields.char('APC(HQ)',size=32,readonly=1),
        'apc':fields.char('APC(HQ)',size=32,readonly=1),
    }
hq_statement_line()

#for view only

class e_statement_line(osv.osv):
    _name="e.statement.line"
    _inherit="hq.statement.line"
    _table="hq_statement_line"
e_statement_line()

