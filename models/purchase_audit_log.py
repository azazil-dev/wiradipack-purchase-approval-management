# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseAuditLog(models.Model):
    _name = 'purchase.audit.log'
    _description = 'Purchase Audit Log'
    _order = 'id desc'
    _rec_name = 'record_name'

    model_name = fields.Char(string='Model', required=True, index=True)
    res_id = fields.Integer(string='Record ID', required=True, index=True)
    record_name = fields.Char(string='Record Name', index=True)
    event = fields.Selection([
        ('create', 'Create'),
        ('write', 'Write'),
        ('unlink', 'Unlink'),
    ], string='Event', required=True, index=True)
    field_name = fields.Char(string='Field Name')
    old_value = fields.Text(string='Old Value')
    new_value = fields.Text(string='New Value')
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, required=True, index=True)
    create_date = fields.Datetime(string='Date', default=fields.Datetime.now, readonly=True)
    ip_address = fields.Char(string='IP Address')

    def write(self, vals):
        raise UserError(_("Audit log records cannot be modified."))

    @api.ondelete(at_uninstall=False)
    def _unlink_protect(self):
        raise UserError(_("Audit log records cannot be deleted."))

