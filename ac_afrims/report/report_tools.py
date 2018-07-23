import os
from osv import osv
import xmlrpclib
from rst2pdf import createpdf
import ho.pisa as pisa
import cStringIO as StringIO
from fdfgen import forge_fdf
import uuid

# jy_serv=xmlrpclib.ServerProxy("http://localhost:9999/")

def pdf_fill(orig_pdf,vals):
    print "pdf_fill",orig_pdf,vals

    fields=[]
    for k,v in vals.items():
        fields.append((k,v,))

    orig_pdf_abs=os.path.join(os.getcwd(),orig_pdf)
    # tmp=os.tempnam()

    #jy_serv.pdf_fill(orig_pdf_abs,tmp,vals)

    # pdf=file(tmp).read()

    data_fdf= '%s.fdf' % uuid.uuid4()
    src_pdf = orig_pdf_abs
    output_pdf = '%s.pdf' % uuid.uuid4()

    fdf = forge_fdf("",fields,[],[],[])
    fdf_file = open(data_fdf,"wb")
    fdf_file.write(fdf)
    fdf_file.close()

    # system command to fill
    #cmd = "/usr/bin/pdftk %s fill_form %s output %s flatten" % (src_pdf,data_fdf,output_pdf,)
    cmd = "/usr/bin/pdftk %s fill_form %s output %s" % (src_pdf,data_fdf,output_pdf)
    os.system(cmd)

    # read to iostream
    pdf=file(output_pdf).read()
    # remove temporay file
    os.unlink(output_pdf)
    os.unlink(data_fdf)

    return pdf

def pdf_merge(pdf1,pdf2):
    try:
        tmp1=os.tempnam()
        tmp2=os.tempnam()
        tmp3=os.tempnam()
        file(tmp1,"w").write(pdf1)
        file(tmp2,"w").write(pdf2)
        cmd="/usr/bin/pdftk %s %s cat output %s"%(tmp1,tmp2,tmp3)
        os.system(cmd)
        pdf3=file(tmp3).read()
        os.unlink(tmp1)
        os.unlink(tmp2)
        os.unlink(tmp3)
        return pdf3
    except:
        raise Exception("Failed to merge PDF files")

def rst2rtf(rst):
    try:
        tmp=os.tempnam()
        cmd="pandoc -s -t rtf -o %s"%tmp
        os.popen(cmd,"w").write(rst)
        rtf=file(tmp).read()
        os.unlink(tmp)
        return rtf
    except Exception,e:
        raise Exception("Failed to create RTF file: %s"%str(e))

def rst2pdf(rst):
    try:
        out=StringIO.StringIO()
        createpdf.RstToPdf().createPdf(text=rst,output=out)
        pdf=out.getvalue()
        return pdf
    except Exception,e:
        raise Exception("Failed to create PDF file: %s"%str(e))

def html2pdf(html):
    try:
        inp=StringIO.StringIO(html)
        out=StringIO.StringIO()
        res=pisa.pisaDocument(inp,out)
        pdf=out.getvalue()
        return pdf
    except Exception,e:
        raise Exception("Failed to create PDF file: %s"%str(e))
