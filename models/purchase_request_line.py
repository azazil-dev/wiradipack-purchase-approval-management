# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class PurchaseRequestLine(models.Model):
    _name = 'purchase.request.line'
    _inherit = ['purchase.audit.mixin']
    _description = 'Purchase Request Line'
    _order = 'id'

    request_id = fields.Many2one(
        'purchase.request',
        string='Purchase Request',
        required=True,
        ondelete='cascade',
        index=True
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True
    )
    name = fields.Text(string='Description', required=True)
    product_qty = fields.Float(string='Quantity', default=1.0, required=True, digits='Product Unit of Measure')
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        required=True,
        domain="[('category_id', '=', product_uom_category_id)]"
    )
    product_uom_category_id = fields.Many2one(
        related='product_id.uom_id.category_id',
        string='Category'
    )
    currency_id = fields.Many2one(
        related='request_id.currency_id',
        string='Currency',
        readonly=True
    )
    estimated_unit_price = fields.Monetary(
        string='Estimated Unit Price',
        currency_field='currency_id',
        required=True,
        default=0.0
    )
    subtotal = fields.Monetary(
        string='Subtotal',
        currency_field='currency_id',
        compute='_compute_subtotal',
        store=True
    )
    suggested_vendor_id = fields.Many2one(
        'res.partner',
        string='Suggested Vendor',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]"
    )
    date_required = fields.Date(
        string='Date Required',
        related='request_id.date_required',
        store=True,
        readonly=False
    )
    company_id = fields.Many2one(
        related='request_id.company_id',
        string='Company',
        store=True,
        readonly=True
    )

    _sql_constraints = [
        (
            'check_product_qty_positive',
            'CHECK(product_qty > 0)',
            'Quantity must be strictly greater than 0.'
        ),
    ]

    @api.depends('product_qty', 'estimated_unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.product_qty * line.estimated_unit_price

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.display_name
            self.product_uom_id = self.product_id.uom_id.id
            self.estimated_unit_price = self.product_id.standard_price
            if self.product_id.seller_ids:
                self.suggested_vendor_id = self.product_id.seller_ids[0].partner_id.id

