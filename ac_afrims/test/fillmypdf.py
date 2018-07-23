#!/usr/bin/python

from fdfgen import forge_fdf
import uuid
import subprocess

datas={
'field1': 'WT0J3Y',
 'field10': u'Russama Jittawisutthikul\nWorrawutL.ca@afrims.org',
 'field11': u'02-696-2754',
 'field11n': u'02-696-2754',
 'field12': 'X',
 'field12_1': 'AR 710-2',
 'field14': '1\n\n',
 'field15': u'Formatter Board for HP LaserJet Printer\n\nSuggested Supplier\n\n\n',
 'field15h': u'Formatter Board for HP LaserJet Pro 400 Color M451dn \r\nfrom world wide com service (http://www.wcs-th.com/)  \r\n\r\nhttp://www.wcs-th.com/003-1030-06059.html',
 'field15n': u'Formatter Board for HP LaserJet Printer\n\nSuggested Supplier\n\n\n',
 'field16': '1.00\n\n',
 'field16n': '1.00\n\n',
 'field17': u'Unit\n\n',
 'field18a': u'3,480.00\n\n',
 'field18ah': u'Baht',
 'field18b': u'3,480.00\n\n',
 'field18bh': u'Baht',
 'field19': u'ESURV / AF\n Total: 0.00 THB\n WBS: ',
 'field1b': u'PR18-00348',
 'field2': '',
 'field20': 'Chadchadaporn P.\n Budget Analyst, FSN-9',
 'field21': '',
 'field22': '',
 'field25': u'test3\n',
 'field27': u'LOUIS R. MACAREO, COL, MC',
 'field28': '',
 'field29': '',
 'field3': '4 April 2018',
 'field30': u'02-6962759',
 'field30n': u'02-6962759',
 'field31': u'SEE A. YANG, SSG, Billing Official',
 'field32': '',
 'field33': '',
 'field34': u'ANTHONY T. SHIEPKO, JR.\nMAJ, MS\nChief, Logistics',
 'field4': 'Purchasing & Contracting Officer\n US Embassy Thailand (GSO)\n APO AP 96546',
 'field5': 'Department of Logistics Procurement \n USAMD-AFRIMS \n APO AP 96546',
 'field6': ' Department of Virology\n USAMD-AFRIMS\n APO AP 96546 ',
 'field7': 'Department of Virology\n USAMD-AFRIMS, APO AP 96546',
 'field8': ' Department of Logistics\n Supply Office, 315/6 Rajvithi Road, Rajthevee, BKK 10400 ',
 'field8n': ' Department of Logistics\n Supply Office, 315/6 Rajvithi Road, Rajthevee, BKK 10400 ',
 'field9': '4 May 2018',
 'fiels15': '',
 'pa': 1,
 'po': 1}

#fields = [('name','John Smith'),('telephone','555-1234')]
fields=[]
for k,v in datas.items():
    fields.append((k,v,))

print(fields)

data_fdf= '%s.fdf' % uuid.uuid4()
src_pdf = 'form_3953.pdf'
output_pdf = '%s.pdf' % uuid.uuid4()

fdf = forge_fdf("",fields,[],[],[])
fdf_file = open(data_fdf,"wb")
fdf_file.write(fdf)
fdf_file.close()

# system command to fill


cmd = "/usr/bin/pdftk %s fill_form %s output %s flatten" % (src_pdf,data_fdf,output_pdf,)
print(cmd)
# subprocess.Popen(cmd,shell=True)
import os
os.system(cmd)
#

#subprocess.Popen("cp %s myoutput.pdf " % ( output_pdf))
# subprocess.Popen("rm %s %s " % ( data_fdf,output_pdf))

