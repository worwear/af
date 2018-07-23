from report.interface import report_int
import pooler
import pydot
import os

class report(report_int):
    def create(self,cr,uid,ids,datas,context={}):
        pool=pooler.get_pool(cr.dbname)
        wiz=pool.get("wiz.print.wkf").browse(cr,uid,ids[0])
        graph=pydot.Dot(graph_type="digraph",rankdir="TB",graph_name="\"Workflow of %s\""%wiz.model_id.name)
        st_ids=pool.get("wkf.state").search(cr,uid,[('model_id','=',wiz.model_id.id)])
        for st in pool.get("wkf.state").browse(cr,uid,st_ids):
            n=pydot.Node(st.name)
            graph.add_node(n)
        dec_ids=pool.get("wkf.decision").search(cr,uid,[('model_id','=',wiz.model_id.id)])
        for dec in pool.get("wkf.decision").browse(cr,uid,dec_ids):
            if len(dec.choices)>1:
                n=pydot.Node(dec.name,shape="diamond",label="")
                graph.add_node(n)
                l=dec.name
                l+="\\n["+",".join([d.role_id.name for d in dec.deciders])+"]"
                e=pydot.Edge(dec.name,dec.name,color="transparent",label='"%s"'%l)
                graph.add_edge(e)
                if not (dec.interface_type=="dialog" and not dec.choice_button):
                    for cond in dec.conditions:
                        e=pydot.Edge(cond.state_from.name,dec.name,label="")
                        graph.add_edge(e)
                i=0
                n=len(dec.choices)
                for ch in dec.choices:
                    i+=1
                    if n==2:
                        p=i==1 and "sw" or "se"
                    elif n==3:
                        p=i==1 and "sw" or i==2 and "s" or "se"
                    else:
                        p="s"
                    if ch.state_to:
                        e=pydot.Edge(dec.name,ch.state_to.name,label=ch.name or "",tailport=p)
                    else:
                        e=pydot.Edge(dec.name,ch.next_decision_id.name,label=ch.name or "",tailport=p)
                    graph.add_edge(e)
            elif len(dec.choices)==1:
                ch=dec.choices[0]
                l=ch.name or ""
                l+="\\n["+",".join([d.role_id.name for d in dec.deciders])+"]"
                for cond in dec.conditions:
                    e=pydot.Edge(cond.state_from.name,ch.state_to.name,label=l)
                    graph.add_edge(e)
        graph.write_ps("wkf.ps")
        os.system("epstopdf wkf.ps > wkf.pdf")
        pdf=file("wkf.pdf").read()
        return (pdf,"pdf")
report("report.wkf")
