# -*- coding: utf-8 -*-
{
    'name': 'PT Wiradi Utama Packindo - Purchase Approval Management',
    'version': '17.0.1.0.0',
    'category': 'Purchases',
    'summary': 'Multi-level purchase request approval based on transaction values, with audit trail and histories',
    'description': """
Purchase Approval Management
============================
Custom module for PT Wiradi Utama Packindo adding:
- Purchase Request (PR) workflow
- Multi-level tiered approval based on transaction value
- Approval history & immutable audit trail
- Separation of duties and role-based access control
- Enforcement and integration with Odoo Purchase Order
    """,
    'author': 'Arif N Ramadhan',
    'website': 'https://www.niits.id',
    'license': 'OPL-1',
    'depends': [
        'base',
        'mail',
        'hr',
        'product',
        'purchase',
        'base_automation',
    ],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'data/ir_sequence_data.xml',
        'data/approval_rule_data.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        'views/purchase_request_wizard_views.xml',
        'views/purchase_request_views.xml',
        'views/purchase_approval_rule_views.xml',
        'views/history_audit_views.xml',
        'views/purchase_order_views.xml',
        'views/res_config_settings_views.xml',
        'views/menus.xml',
        'report/purchase_request_report.xml',
        'report/purchase_order_report.xml',
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

