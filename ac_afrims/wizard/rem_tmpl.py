import wizard
import pooler

view="""<?xml version="1.0"?>
<form string="Add remarks from templates">
    <field name="templates" colspan="4" nolabel="1"/>
</form>
"""

fields={
    "templates": {
        "type": "many2many",
        "string": "Templates",
        "relation": "remark.template",
    },
}

class rem_tmpl(wizard.interface):
    def _add(self,cr,uid,data,context):
        print "_add"
        pool=pooler.get_pool(cr.dbname)
        tdy_id=data["id"]
        tdy=pool.get("tdy.request").browse(cr,uid,tdy_id)
        tmpl_ids=data["form"]["templates"][0][2]
        notes=tdy.notes or ""
        for tmpl in pool.get("remark.template").browse(cr,uid,tmpl_ids):
            notes+="\n"+tmpl.name
        pool.get("tdy.request").write(cr,uid,tdy_id,{"notes":notes})
        return {}

    states={
        "init": {
            "actions": [],
            "result": {
                "type": "form",
                "arch": view,
                "fields": fields,
                "state": [("end","Cancel"),("add","Add to TDY request")],
            },
        },
        "add": {
            "actions": [],
            "result": {
                "type": "action",
                "action": _add,
                "state": "end",
            },
        },
    }
rem_tmpl("rem.tmpl")
