import wizard
import pooler
from tools.misc import UpdateableStr,UpdateableDict

wiz_arch=UpdateableStr()
wiz_fields=UpdateableDict()

arch2="""<?xml version="1.0"?>
<form string="Confirmation">
    <field name="msg" colspan="4" nolabel="1"/>
</form>
"""

fields2={
    "msg": {
        "type": "text",
        "string": "Message",
        "readonly": True,
    }
}

class wkf_choice(wizard.interface):
    def _check(self,cr,uid,data,context):
        #print "_check",data,context
        decision_id=data.get("decision_id")
        if not decision_id:
            decision_id=context.get("decision_id")
            if not decision_id:
                raise wizard.except_wizard("Error","Missing context data")
            data["decision_id"]=decision_id
        pool=pooler.get_pool(cr.dbname)
        dec=pool.get("wkf.decision").browse(cr,uid,decision_id)
        model=dec.model_id.model
        data["model"]=model
        obj_id=data["id"]
        data["obj_id"]=obj_id
        if dec.interface_type=="buttons":
            choice_id=context["choice_id"]
            data["choice_id"]=choice_id
        user=pool.get("res.users").browse(cr,uid,uid)
        emp=user.employee_id
        emp_id=emp.id
        data["employee_id"]=emp_id
        obj=pool.get(model).browse(cr,uid,obj_id)
        decider_id=None
        for decider in dec.deciders:
            if decider.condition and not eval(decider.condition,{"object":obj}):
                continue
            if not decider.role_id.has_role(uid,emp_id,obj):
                continue
            decider_id=decider.id
            break
        if not decider_id:
            raise wizard.except_wizard("Error","You are not authorized to make this decision")
        data["decider_id"]=decider_id
        if dec.interface_type=="buttons":
            return "chosen"
        elif dec.interface_type=="dialog":
            return "choose"

    def _choose(self,cr,uid,data,context):
        #print "_choose",data,context
        pool=pooler.get_pool(cr.dbname)
        obj_id=data["obj_id"]
        model=data["model"]
        dec_id=data["decision_id"]
        dec=pool.get("wkf.decision").browse(cr,uid,dec_id)
        wiz_fields.clear()
        wiz_arch.string='<?xml version="1.0"?>\n'
        wiz_arch.string+='<form string="%s">\n'%(dec.choice_title or "Please choose")
        if dec.choice_type=="one":
            wiz_arch.string+='<field name="choice"/>\n'
            sel=[]
            for ch in dec.choices:
                sel.append((str(ch.id),ch.name))
            wiz_fields["choice"]={
                "type": "selection",
                "selection": sel,
                "string": dec.choice_field or "Choice",
                "required": True,
            }
        elif dec.choice_type=="many":
            for ch in dec.choices:
                wiz_arch.string+='<field name="choice_%d"/><newline/>\n'%ch.id
                wiz_fields["choice_%d"%ch.id]={
                    "type": "boolean",
                    "string": ch.name,
                }
        wiz_arch.string+='</form>\n'
        return {}

    def _chosen(self,cr,uid,data,context):
        #print "_chosen",data,context
        pool=pooler.get_pool(cr.dbname)
        dec=pool.get("wkf.decision").browse(cr,uid,data["decision_id"])
        ch_id=None
        if dec.interface_type=="buttons":
            ch_id=data["choice_id"]
        elif dec.interface_type=="dialog":
            if dec.choice_type=="one":
                ch_id=int(data["form"]["choice"])
        if not ch_id:
            return "record"
        ch=pool.get("decision.choice").browse(cr,uid,ch_id)
        if ch.confirm:
            return "confirm"
        else:
            return "record"

    def _confirm(self,cr,uid,data,context):
        #print "_confirm",data,context
        pool=pooler.get_pool(cr.dbname)
        dec=pool.get("wkf.decision").browse(cr,uid,data["decision_id"])
        ch_id=None
        if dec.interface_type=="buttons":
            ch_id=data["choice_id"]
        elif dec.interface_type=="buttons":
            if dec.choice_type=="one":
                ch_id=int(data["form"]["choice"])
        ch=pool.get("decision.choice").browse(cr,uid,ch_id)
        return {"msg": ch.confirm}

    def _record(self,cr,uid,data,context):
        #print "_record",data,context
        pool=pooler.get_pool(cr.dbname)
        obj_id=data["obj_id"]
        model=data["model"]
        obj=pool.get(model).browse(cr,uid,obj_id)
        dec_id=data["decision_id"]
        decider_id=data["decider_id"]
        emp_id=data["employee_id"]
        dec=pool.get("wkf.decision").browse(cr,uid,dec_id)
        next_id=None
        if dec.interface_type=="buttons":
            ch_id=data["choice_id"]
            pool.get("wkf.decision").record_choice(pool.get(model),cr,uid,[obj_id],dec_id,decider_id,emp_id,ch_id,uid)
            ch=pool.get("decision.choice").browse(cr,uid,ch_id)
            if ch.next_decision_id:
                next_id=ch.next_decision_id.id
        elif dec.interface_type=="dialog":
            if dec.choice_type=="one":
                ch_id=int(data["form"]["choice"])
                pool.get("wkf.decision").record_choice(pool.get(model),cr,uid,[obj_id],dec_id,decider_id,emp_id,ch_id,uid)
                ch=pool.get("decision.choice").browse(cr,uid,ch_id)
                if ch.next_decision_id:
                    next_id=ch.next_decision_id.id
            elif dec.choice_type=="many":
                for field,val in data["form"].items():
                    if val:
                        ch_id=int(field.split("_")[-1])
                        pool.get("wkf.decision").record_choice(pool.get(model),cr,uid,[obj_id],dec_id,decider_id,emp_id,ch_id,uid)
        if next_id:
            data["decision_id"]=next_id
            return "init"
        else:
            return "apply"

    def _apply(self,cr,uid,data,context):
        #print "_apply",data,context
        pool=pooler.get_pool(cr.dbname)
        model=data["model"]
        obj_id=data["obj_id"]
        pool.get("wkf.decision").apply_choices(pool.get(model),cr,uid,[obj_id])
        return {}

    states={
        "init": {
            "actions": [],
            "result": {
                "type": "choice",
                "next_state": _check,
            },
        },
        "choose": {
            "actions": [_choose],
            "result": {
                "type": "form",
                "arch": wiz_arch,
                "fields": wiz_fields,
                "state": [("chosen","Continue"),("end","Cancel")],
            },
        },
        "chosen": {
            "actions": [],
            "result": {
                "type": "choice",
                "next_state": _chosen,
            },
        },
        "confirm": {
            "actions": [_confirm],
            "result": {
                "type": "form",
                "arch": arch2,
                "fields": fields2,
                "state": [("record","Confirm"),("end","Cancel")],
            },
        },
        "record": {
            "actions": [],
            "result": {
                "type": "choice",
                "next_state": _record,
            },
        },
        "apply": {
            "actions": [],
            "result": {
                "type": "action",
                "action": _apply,
                "state": "end",
            },
        },
    }
wkf_choice("wkf.choice")
