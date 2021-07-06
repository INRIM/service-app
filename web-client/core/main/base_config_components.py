# Copyright INRIM (https://www.inrim.eu)
# Author Alessio Gerace @Inrim
# See LICENSE file for full licensing details.

alert_base = {
    "succcess": {
        "alert_type": "success",
        "message": "Dati aggiornati con successo",
        "add_class": " mx-auto col-6 ",
        "hide_close_btn": True
    },
    "error": {
        "alert_type": "danger",
        "message": "Errore aggiornamento dati",
        "add_class": "  mx-auto col-6 ",
        "hide_close_btn": True,
    },
    "warning": {
        "alert_type": "warning",
        "message": "Errore aggiornamento dati",
        "add_class": "  mx-auto col-6 ",
        "hide_close_btn": True,
    },
}

chips_base = {
    "base": {
        "alert_type": "primary",
        "label": "Selezionare",
        "icon": "it-info-circle"
    },
    "secondary": {
        "alert_type": "secondary",
        "label": "Selezionare",
        "icon": "it-info-circle"
    },
    "success": {
        "alert_type": "success",
        "label": "Ok",
        "icon": "it-check-circle"
    },
    "error": {
        "alert_type": "danger",
        "label": "Attenzione mancano tutti i dati",
        "icon": "it-error"
    },
    "warning": {
        "alert_type": "warning",
        "label": "Attenzione mancano alcuni dati",
        "icon": "it-warning-circle"
    },
}

button = {
    "submit": {
        "name": "",
        "type": "submit",
        "btn_class": False,
        "link": ""
    },
    "link": {
        "name": "",
        "type": "submit",
        "btn_class": False,
        "link": ""
    },
    "button": {
        "name": "",
        "type": "button",
        "btn_class": "False",
        "link": ""
    }
}

form_component_map = {
    "textarea": "form_text_area.html",
    "address": "",
    "component": "",
    "componentmodal": "",
    "button": "buttons/button.html",
    "ctxbuttonaction": "buttons/context_button_action.html",
    "buttonaction": "buttons/button_action.html",
    "modalbutton": "buttons/modal_button.html",
    "checkbox": "checkbox/form_toggle.html",
    "blockcolumns": "block_row.html",
    "columns": "form_row.html",
    "column": "form_col.html",
    "container": "page_container/container.html",
    "content": "block_container_html.html",
    "currency": "",
    "datagrid": "datagrid/datagrid.html",
    "datagridRow": "datagrid/datagrid_row.html",
    "datamap": "",
    "datetime": "datetime/form_date_time.html",
    "day": "",
    "editgrid": "",
    "email": "input/form_input.html",
    "input": "input/form_input.html",
    "field": "",
    "multivalue": "",
    "fieldset": "",
    "file": "form_upload_file.html",
    "form": "page_form/form.html",
    "list_view": "page_form/list_view.html",
    "project": "page_form/form.html",
    "layout": "page_layout/page_hero_builder.html",
    "menu": "menu/menu_dropdown.html",
    "hidden": "",
    "nested": "",
    "nesteddata": "",
    "nestedarray": "",
    "number": "input/form_number_input.html",
    "panel": "block_card_components.html",
    "password": "input/form_password_input.html",
    "phoneNumber": "input/form_input.html",
    "radio": "form_radio_container.html",
    "recaptcha": "",
    "resource": "select/form_select_search.html",
    "select": "select/form_select_search.html",
    "selectmulti": "select/form_select_multi.html",
    "signature": "",
    "survey": "survey/survey.html",
    "surveyRow": "survey/survey_row.html",
    "table": "table/tabledatatable.html",
    "tabs": "tabs/form_tabs.html",
    "tags": "",
    "textfield": "input/form_input.html",
    "time": "",
    "tree": "",
    "unknown": "UnknownComponent",
    "url": "text_input.html",
    "htmlelement": "icon_link.html",
    "well": "",
    "info": "info_readonly_block.html",
    "search_area": "search_area/search_area.html",
    "formio_builder_container": "formio/builder_frame.html",
    "formio_builder": "formio/builder.html"
}

form_component_default_cfg = {
    "key": "key",
    "description": "desc",
    "action": "type",
    "data": {"values": "options"},
    "defaultValue": "value",
    "values": "rows",
    "validate": {"required": "required"},
    "property": {"onchange": "onchange"},
}

custom_builder_oject = {
    "title": "Inrim Fields",
    "weight": 10,
    "components": {
        "uid": {
            "title": "Inrim id",
            "key": "inrim_uid",
            "icon": "user-secret",
            "schema": {
                "label": "User uid",
                "type": "textfield",
                "key": "uid",
                "input": True,
                "hidden": True,
                "tableView": False
            }
        },
        "inrim_users": {
            "title": "Utenti",
            "key": "inrim_users",
            "icon": "address-book-o",
            "schema": {
                "label": "Utenti",
                "key": "user",
                "type": "select",
                "dataSrc": "url",
                "data": {
                    "url": "https://people.ininrim.it/api/get_addressbook_service_user/0",
                    "headers": [
                        {
                            "key": "x-key",
                            "value": "people_key"
                        }
                    ]
                },
                "properties": {
                    "label": "full_name",
                    "id": "uid"
                }
            }
        },
        "inrim_divuo": {
            "title": "Div/UO Select",
            "key": "inrim_divuo",
            "icon": "cube",
            "schema": {
                "label": "Divisione/U.O.",
                "key": "divuo",
                "type": "select",
                "dataSrc": "url",
                "selectValues": "result",
                "data": {
                    "url": "https://people.ininrim.it/api/getsectors/",
                    "headers": [
                        {
                            "key": "x-key",
                            "value": "people_key"
                        }
                    ]
                },
                "properties": {
                    "label": "name",
                    "id": "id"
                }
            }
        },
        "inrim_perstype": {
            "title": "Tipo Personale",
            "key": "inrim_perstype",
            "icon": "users",
            "schema": {
                "label": "Tipo Personale",
                "type": "select",
                "key": "personal_type",
                "dataSrc": "url",
                "data": {
                    "url": "https://people.ininrim.it/api/getpersonaltypes",
                    "headers": [
                        {
                            "key": "x-key",
                            "value": "people_key"
                        }
                    ]
                },
                "properties": {
                    "label": "name",
                    "id": "id"
                }
            }
        },
        "inrim_workmodes": {
            "title": "Tipo Lavoro",
            "key": "inrim_workmodes",
            "icon": "briefcase",
            "schema": {
                "label": "Modalità lavorativa",
                "type": "select",
                "key": "work_mode",
                "dataSrc": "url",
                "data": {
                    "url": "https://people.ininrim.it/api/getworkmodes",
                    "headers": [
                        {
                            "key": "x-key",
                            "value": "people_key"
                        }
                    ]
                },
                "properties": {
                    "label": "name",
                    "id": "id"
                }
            }
        },
        "inrim_buildings": {
            "title": "Edifici Locali",
            "key": "inrim_rooms",
            "icon": "building-o",
            "schema": {
                "label": "Locali",
                "type": "select",
                "key": "rooms",
                "dataSrc": "url",
                "data": {
                    "url": "https://people.ininrim.it/api/get_rooms",
                    "headers": [
                        {
                            "key": "x-key",
                            "value": "people_key"
                        }
                    ]
                },
                "properties": {
                    "label": "name",
                    "id": "id"
                }
            }
        },
        "inrim_link": {
            "title": "Link",
            "key": "inrim_link",
            "icon": "link",
            "schema": {
                "label": "New Link",
                "type": "htmlelement",
                "key": "ilink",
                "tag": "a",
                "content": "https://...",
                "customClass": "mx-auto col-md-8 mt-1 mb-1",
                "attrs": [
                    {
                        "attr": "target",
                        "value": "_blank"
                    },
                    {
                        "attr": "direction",
                        "value": ""
                    }
                ]
            }
        }
    }
}
