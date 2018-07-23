#!/usr/bin/env jython

import sys

sys.path.append("/usr/share/java/itext.jar")

from java.io import FileOutputStream
from com.lowagie.text.pdf import PdfReader,PdfStamper,BaseFont
#from com.itext.text.pdf import PdfReader,PdfStamper,BaseFont
import re
import time
import xmlrpclib
from SimpleXMLRPCServer import SimpleXMLRPCServer

def pdf_fill(orig_pdf,new_pdf,vals):
    print "pdf_fill",orig_pdf,new_pdf,vals
    t0=time.time()
    rd=PdfReader(orig_pdf)
    st=PdfStamper(rd,FileOutputStream(new_pdf))
    form=st.getAcroFields()
    for k,v in vals.items():
        try:
            form.setField(k,str(v))
        except Exception,e:
            raise Exception("Field %s: %s"%(k,str(e)))
    #st.setFormFlattening(True)
    st.setFormFlattening(False) # for editable PDF
    st.close()
    t1=time.time()
    print "finished in %.2fs"%(t1-t0)
    return True

def pdf_merge(pdf1,pdf2):
    print "pdf_merge",orig_pdf,vals
    t0=time.time()
    pdf=pdf1
    t1=time.time()
    print "finished in %.2fs"%(t1-t0)
    return pdf

serv=SimpleXMLRPCServer(("localhost",9999))
serv.register_function(pdf_fill,"pdf_fill")
#serv.register_function(pdf_merge,"pdf_merge")
print "waiting for requests..."
serv.serve_forever()
