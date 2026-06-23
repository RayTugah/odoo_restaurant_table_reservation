# Copyright 2026 RayTugah
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html).
{
    'name': 'Restaurant Table Reservation',
    'version': '19.0.1.0.0',
    'category': 'Restaurant',
    'summary': 'Restaurant table reservation management with table tags, tickets, wizards and daily reservation reports.',
    'description': '''
Restaurant Table Reservation
============================

This module provides an independent restaurant table reservation workflow for Odoo:

- Table reservation model based on the stable Camping Fuente use case.
- Reservation tags and Kanban indicators.
- Reservation creation wizard.
- Daily ticket report for kitchen/service coordination.
- Optional links with POS tickets, sales orders and pool/day-capacity reservations when those models exist in the target database.
- Migration helpers for installations that previously used an Odoo Studio model.

The Camping Fuente implementation is the reference production use case. The addon keeps the proven technical field structure used in that deployment in order to make upgrades and migrations safer.
''',
    'author': 'RayTugah',
    'maintainers': ['RayTugah'],
    'website': 'https://github.com/RayTugah/odoo-restaurant-table-reservation',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'mail',
        'base_automation',
        'calendar',
        'contacts',
        'product',
        'sale',
        'pos_restaurant',
        'pool_reservation_capacity',
    ],
    'data': [
        'data/ir_model.xml',
        'data/ir_model_fields.xml',
        'security/ir.model.access.csv',
        'data/default_tags.xml',
        'views/reserva_mesas_wizard_views.xml',
        'views/reserva_mesas_print_fecha_wizard_views.xml',
        'data/ir_actions_report.xml',
        'data/ir_actions_server.xml',
        'data/ir_ui_view.xml',
        'data/ir_actions_act_window.xml',
        'data/ir_actions_act_window_view.xml',
        'data/ir_ui_menu.xml',
        'data/base_automation.xml',
        'data/ir_model_access.xml',
        'data/ir_default.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
}
