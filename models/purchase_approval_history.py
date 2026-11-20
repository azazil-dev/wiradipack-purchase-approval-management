# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseApprovalHistory(models.Model):
    _name = 'purchase.approval.history'
    _description = 'Purchase Approval History'
    _order = 'id desc'

    request_id = fields.Many2one(
        'purchase.request',
        string='Purchase Request',
        required=True,
        ondelete='cascade',
        index=True
    )
    round_no = fields.Integer(string='Round', required=True, default=1, index=True)
    level = fields.Selection([
        ('supervisor', 'Supervisor'),
        ('manager', 'Manager'),
        ('director', 'Director'),
    ], string='Level')
    action = fields.Selection([
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('revised', 'Revised'),
        ('cancelled', 'Cancelled'),
        ('escalated', 'Escalated'),
        ('reminded', 'Reminded'),
        ('po_created', 'PO Created'),
    ], string='Action', required=True, index=True)
    actor_id = fields.Many2one(
        'res.users',
        string='Actor',
        required=True,
        default=lambda self: self.env.user,
        index=True
    )
    action_date = fields.Datetime(
        string='Action Date',
        default=fields.Datetime.now,
        required=True,
        readonly=True
    )
    comment = fields.Text(string='Comment')
    state_from = fields.Char(string='State From')
    state_to = fields.Char(string='State To')
    amount_snapshot = fields.Monetary(
        string='Amount Snapshot',
        currency_field='currency_id',
        readonly=True
    )
    currency_id = fields.Many2one(
        related='request_id.currency_id',
        string='Currency',
        readonly=True
    )
    company_id = fields.Many2one(
        related='request_id.company_id',
        string='Company',
        store=True,
        readonly=True
    )

    def write(self, vals):
        raise UserError(_("Approval history records cannot be modified."))

    @api.ondelete(at_uninstall=False)
    def _unlink_protect(self):
        raise UserError(_("Approval history records cannot be deleted."))

