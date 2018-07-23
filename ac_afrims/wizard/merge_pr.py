import wizard
import pooler

view="""<?xml version="1.0"?>
<form string="Merge Purchase Requests">
<label string="This will merge the selected purchase requests" colspan="4"/>
</form>
"""

class merge_pr(wizard.interface):
    def _merge(self,cr,uid,data,context):
        print "_merge",data,context
        pool=pooler.get_pool(cr.dbname)
        ids=data["ids"]
        new_id=pool.get("purchase.request").merge(cr,uid,ids)
        all_ids=ids+[new_id]
        return {
            "type": "ir.actions.act_window",
            "res_model": "purchase.request",
            "view_type": "form",
            "view_mode": "tree,form",
            "domain": "[('id','in',(%s))]"%(",".join([str(id) for id in all_ids])),
            "name": "Purchase Requests",
        }

    states={
        "init": {
            "actions": [],
            "result": {
                "type": "form",
                "arch": view,
                "fields": {},
                "state": [("end","Cancel"),("merge","Merge")],
            },
        },
        "merge": {
            "actions": [],
            "result": {
                "type": "action",
                "action": _merge,
                "state": "end",
            },
        },
    }
merge_pr("merge.pr")
