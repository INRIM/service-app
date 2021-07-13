# Copyright INRIM (https://www.inrim.eu)
# Author Alessio Gerace @Inrim
# See LICENSE file for full licensing details.
import json


class EmailTemplate:

    def __init__(self):
        super()
        self.rows = []
        self.curr_row = 0
        self.curr_col = 0
        self.tmp_base = {
            "name": "email_template_notification",
            "view_type": "mail",
            "replace_keys": [],
            "fields": []
        }

    def get_template(self):
        self.tmp_base['fields'] = self.rows
        return self.tmp_base

    def add_block_text_link(self, value, cls="", link="", rowid=0, newrow=True):
        if newrow and rowid == 0:
            self.new_row()
            row = self.curr_row
        else:
            row = rowid
        self.curr_col = len(self.rows[row]['fields'])
        tmp_txt = {
            "text_link_base": {
                "name": f"row{self.curr_row}_{self.curr_col}",
                "link": link,
                "cls": cls,
                "value": value
            }
        }
        self.rows[row]['fields'].append(tmp_txt)

    def add_block_text(self, value, cls="", rowid=0, newrow=True):
        if newrow and rowid == 0:
            self.new_row()
            row = self.curr_row
        else:
            row = rowid
        self.curr_col = len(self.rows[row]['fields'])
        tmp_txt = {
            "text_block_base": {
                "name": f"row{self.curr_row}_{self.curr_col}",
                "value": value,
                "cls": cls
            }
        }
        self.rows[row]['fields'].append(tmp_txt)

    def new_row(self):
        self.curr_col = 0
        self.rows.append({"fields": []})
        self.curr_row = len(self.rows) - 1
