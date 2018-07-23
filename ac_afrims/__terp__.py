##############################################################################
#
#    Copyright (C) 2009 Almacom (Thailand) Ltd.
#    All rights reserved.
#    http://almacom.co.th/
#
##############################################################################

{
    'name': 'AFRIMS Module',
    'version': '1.0',
    'description': """
Custom module for AFRIMS (purchasing, budget, logistics).
    """,
    'author': 'Almacom Ltd.',
    'website': 'http://almacom.co.th/',
    'depends': ['base','stock','hr'],
    'init_xml': [],
    'update_xml': [
        "af_data.xml",
        "hq_statement_view.xml",

        "hq_statement_hq_pr_view.xml",
        "hq_statement_hq_tdy_view.xml",

        "hq_statement_e_pr_view.xml",
        "hq_statement_e_tdy_view.xml",

        "hq_statement_line_view.xml",
        "af_view.xml",
        "wizard/hq_line_gen_view.xml",
        "wizard/import_hq_statement_view.xml",
        "wizard/e_statement_gen_view.xml",
        "security/ir.model.access.csv",
    ],
    'installable': True,
    'active': False,
}
