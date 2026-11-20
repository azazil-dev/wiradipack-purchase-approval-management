# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PurchaseApprovalRule(models.Model):
    _name = 'purchase.approval.rule'
    _inherit = ['purchase.audit.mixin']
    _description = 'Purchase Approval Rule'
    _order = 'sequence, min_amount, id'

    name = fields.Char(string='Rule Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    level = fields.Selection([
        ('supervisor', 'Supervisor'),
        ('manager', 'Manager'),
        ('director', 'Director'),
    ], string='Approval Level', required=True)
    min_amount = fields.Monetary(string='Minimum Amount', currency_field='currency_id', required=True, default=0.0)
    max_amount = fields.Monetary(
        string='Maximum Amount',
        currency_field='currency_id',
        help='Maximum transaction amount for this level. Leave empty or 0 for unlimited.'
    )
    group_id = fields.Many2one('res.groups', string='Approver Group', required=True)
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        string='Currency',
        readonly=True
    )

    _sql_constraints = [
        (
            'check_min_amount_positive',
            'CHECK(min_amount >= 0)',
            'Minimum amount must be greater than or equal to 0.'
        ),
        (
            'check_max_amount_greater',
            'CHECK(max_amount = 0 OR max_amount IS NULL OR max_amount > min_amount)',
            'Maximum amount must be greater than minimum amount if set.'
        ),
    ]

    @api.constrains('min_amount', 'max_amount', 'active', 'company_id')
    def _check_no_overlap(self):
        for rule in self:
            if not rule.active:
                continue

            # Ambil semua aturan aktif dalam company yang sama
            domain = [
                ('active', '=', True),
                ('company_id', '=', rule.company_id.id),
                ('id', '!=', rule.id),
            ]
            other_rules = self.search(domain)

            current_min = rule.min_amount
            current_max = rule.max_amount if (rule.max_amount and rule.max_amount > 0) else float('inf')

            for other in other_rules:
                other_min = other.min_amount
                other_max = other.max_amount if (other.max_amount and other.max_amount > 0) else float('inf')

                # Rentang [current_min, current_max] tumpang tindih dengan [other_min, other_max]
                # jika current_min <= other_max dan other_min <= current_max
                if max(current_min, other_min) <= min(current_max, other_max):
                    raise ValidationError(_(
                        "Approval rule '%(rule_name)s' (%(min)s - %(max)s) overlaps with rule '%(other_name)s' (%(o_min)s - %(o_max)s).",
                        rule_name=rule.name,
                        min=current_min,
                        max=rule.max_amount or 'Unlimited',
                        other_name=other.name,
                        o_min=other_min,
                        o_max=other.max_amount or 'Unlimited'
                    ))

