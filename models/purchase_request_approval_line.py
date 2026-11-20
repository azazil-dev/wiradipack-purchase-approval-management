# -*- coding: utf-8 -*-
from odoo import models, fields


class PurchaseRequestApprovalLine(models.Model):
    _name = 'purchase.request.approval.line'
    _description = 'Purchase Request Approval Line'
    _order = 'round_no asc, sequence asc, id asc'

    request_id = fields.Many2one(
        'purchase.request',
        string='Purchase Request',
        required=True,
        ondelete='cascade',
        index=True
    )
    round_no = fields.Integer(string='Round', default=1, required=True, index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    level = fields.Selection([
        ('supervisor', 'Supervisor'),
        ('manager', 'Manager'),
        ('director', 'Director'),
    ], string='Level', required=True)
    group_id = fields.Many2one('res.groups', string='Approver Group', required=True)
    state = fields.Selection([
        ('waiting', 'Waiting'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('skipped', 'Skipped'),
    ], string='Status', default='waiting', required=True, index=True)
    approver_id = fields.Many2one('res.users', string='Approver', readonly=True)
    action_date = fields.Datetime(string='Action Date', readonly=True)
    comment = fields.Text(string='Comment')
    company_id = fields.Many2one(
        related='request_id.company_id',
        string='Company',
        store=True,
        readonly=True
    )

