# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    pr_approval_mode = fields.Selection([
        ('highest_only', 'Highest Level Only'),
        ('cumulative', 'Cumulative Multi-Level'),
    ], string='Approval Mode', default='highest_only', required=True)

    pr_po_tolerance = fields.Float(
        string='PO Amount Tolerance (%)',
        default=5.0,
        help='Percentage by which PO amount may exceed approved PR amount.'
    )

    enforce_pr_on_po = fields.Boolean(
        string='Enforce PR on Purchase Orders',
        default=True,
        help='If checked, PO confirmation is blocked if not linked to an approved PR.'
    )

    pr_reminder_days = fields.Integer(
        string='Approval Reminder SLA (Days)',
        default=2,
        help='Working days before sending reminder to pending approver. 0 to disable.'
    )

    pr_escalation_days = fields.Integer(
        string='Approval Escalation SLA (Days)',
        default=5,
        help='Working days before escalating pending PR. 0 to disable.'
    )

    pr_stale_draft_days = fields.Integer(
        string='Stale Draft Reminder (Days)',
        default=30,
        help='Days before reminding requester of stale draft PRs.'
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pr_approval_mode = fields.Selection(
        related='company_id.pr_approval_mode',
        readonly=False,
        string='Approval Mode'
    )
    pr_po_tolerance = fields.Float(
        related='company_id.pr_po_tolerance',
        readonly=False,
        string='PO Amount Tolerance (%)'
    )
    enforce_pr_on_po = fields.Boolean(
        related='company_id.enforce_pr_on_po',
        readonly=False,
        string='Enforce PR on Purchase Orders'
    )
    pr_reminder_days = fields.Integer(
        related='company_id.pr_reminder_days',
        readonly=False,
        string='Approval Reminder SLA (Days)'
    )
    pr_escalation_days = fields.Integer(
        related='company_id.pr_escalation_days',
        readonly=False,
        string='Approval Escalation SLA (Days)'
    )
    pr_stale_draft_days = fields.Integer(
        related='company_id.pr_stale_draft_days',
        readonly=False,
        string='Stale Draft Reminder (Days)'
    )
