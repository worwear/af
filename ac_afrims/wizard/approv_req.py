import wizard
import pooler

view="""<?xml version="1.0"?>
<form string="Add approval request">
    <field name="employee_id"/>
</form>
"""

fields={
    "employee_id": {
        "type": "many2one",
        "relation": "employee",
        "string": "Employee",
        "required": True,
    },
}

class approv_req(wizard.interface):
    def _request(self,cr,uid,data,context):
        print "_request"
        obj_id=data["id"]
        model=context.get("model")
        if not model:
            raise wizard.except_wizard("Error","Missing context")
        pool=pooler.get_pool(cr.dbname)
        obj=pool.get(model).browse(cr,uid,obj_id)
        emp_id=data["form"]["employee_id"]
        emp=pool.get("employee").browse(cr,uid,emp_id)
        if not emp.email:
            raise wizard.except_wizard("Error","Employee '%s' has no email configured"%emp.full_name)
        tmpl="""You approval is requested for [[object.name]]."""
        def replace(match):
            expr=match.group(0)[2:-2]
            res=eval(expr,{"object":obj,"emp":emp})
            return str(res)
        email=re.sub("(\[\[.+?\]\])",replace,tmpl)
        if not email:
            raise osv.except_osv("Error","Email body is empty")
        #tools.email_send("donotreply@afrims.org",[emp.email],"Request from purchase system",email)
        tools.email_send("donotreply@afrims.org",["david.j@almacom.co.th"],"Request from purchase system",email)
        # XXX: TODO
        vals={
            "decision_id": dec.id,
            "type": "request",
            "decider_id": decider.id,
            "employee_id": emp_id,
        }
        obj.write({"history":[(0,0,vals)]})
        return {}

    states={
        "init": {
            "actions": [],
            "result": {
                "type": "form",
                "arch": view,
                "fields": fields,
                "state": [("end","Cancel"),("request","Request approval")],
            },
        },
        "request": {
            "actions": [],
            "result": {
                "type": "action",
                "action": _request,
                "state": "end",
            },
        },
    }
approv_req("approv.req")
