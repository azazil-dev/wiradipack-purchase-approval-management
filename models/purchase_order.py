# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    purchase_request_id = fields.Many2one(
        'purchase.request',
        string='Purchase Request',
        readonly=True,
        copy=False,
        index=True
    )

    def action_view_purchase_request(self):
        self.ensure_one()
        return {
            'name': _('Purchase Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.request',
            'res_id': self.purchase_request_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def button_confirm(self):
        for order in self:
            if order.company_id.enforce_pr_on_po:
                if not order.purchase_request_id:
                    raise UserError(_(
                        "Enforcement Policy: Purchase Orders must be linked to an approved Purchase Request before confirmation."
                    ))
                if order.purchase_request_id.state not in ('approved', 'done'):
                    raise UserError(_(
                        "Enforcement Policy: Linked Purchase Request %s is not in 'Approved' or 'Done' status."
                    ) % order.purchase_request_id.name)
        return super().button_confirm()


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    request_line_id = fields.Many2one(
        'purchase.request.line',
        string='Purchase Request Line',
        readonly=True,
        copy=False
    )

