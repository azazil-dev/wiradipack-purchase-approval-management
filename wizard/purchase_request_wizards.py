# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class PurchaseRequestRejectWizard(models.TransientModel):
    _name = 'purchase.request.reject.wizard'
    _description = 'Purchase Request Reject Wizard'

    request_id = fields.Many2one(
        'purchase.request',
        string='Purchase Request',
        required=True,
        default=lambda self: self.env.context.get('active_id')
    )
    reason = fields.Text(string='Reason for Rejection', required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        if not self.reason or not self.reason.strip():
            raise ValidationError(_("A valid reason is required to reject the Purchase Request."))
        return self.request_id.action_reject(reason=self.reason.strip())


class PurchaseRequestMakePoWizard(models.TransientModel):
    _name = 'purchase.request.make.po.wizard'
    _description = 'Purchase Request Make PO Wizard'

    request_id = fields.Many2one(
        'purchase.request',
        string='Purchase Request',
        required=True,
        default=lambda self: self.env.context.get('active_id')
    )
    line_ids = fields.One2many(
        'purchase.request.make.po.wizard.line',
        'wizard_id',
        string='Lines to Order'
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            request = self.env['purchase.request'].browse(active_id)
            if request.state != 'approved':
                raise UserError(_("Purchase Orders can only be created from Approved Purchase Requests."))
            lines_data = []
            for line in request.line_ids:
                lines_data.append((0, 0, {
                    'request_line_id': line.id,
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'product_qty': line.product_qty,
                    'product_uom_id': line.product_uom_id.id,
                    'estimated_unit_price': line.estimated_unit_price,
                    'partner_id': line.suggested_vendor_id.id if line.suggested_vendor_id else False,
                    'selected': True,
                }))
            res['line_ids'] = lines_data
        return res

    def action_create_po(self):
        self.ensure_one()
        selected_lines = self.line_ids.filtered(lambda l: l.selected)
        if not selected_lines:
            raise UserError(_("Please select at least one line to create a Purchase Order."))

        # Pastikan semua line memiliki vendor
        missing_vendor_lines = selected_lines.filtered(lambda l: not l.partner_id)
        if missing_vendor_lines:
            raise ValidationError(_(
                "Vendor is required for all selected lines. Please specify vendor for: %s"
            ) % ", ".join(missing_vendor_lines.mapped('product_id.display_name')))

        po_obj = self.env['purchase.order']
        po_line_obj = self.env['purchase.order.line']
        created_pos = po_obj.browse()

        # Kelompokkan baris per vendor
        vendors = selected_lines.mapped('partner_id')
        for vendor in vendors:
            vendor_lines = selected_lines.filtered(lambda l: l.partner_id == vendor)
            po_vals = {
                'partner_id': vendor.id,
                'company_id': self.request_id.company_id.id,
                'currency_id': self.request_id.currency_id.id,
                'origin': self.request_id.name,
                'purchase_request_id': self.request_id.id,
                'date_order': fields.Datetime.now(),
            }
            po = po_obj.create(po_vals)
            created_pos |= po

            for w_line in vendor_lines:
                po_line_obj.create({
                    'order_id': po.id,
                    'product_id': w_line.product_id.id,
                    'name': w_line.name,
                    'product_qty': w_line.product_qty,
                    'product_uom': w_line.product_uom_id.id,
                    'price_unit': w_line.estimated_unit_price,
                    'date_planned': self.request_id.date_required or fields.Date.today(),
                    'request_line_id': w_line.request_line_id.id,
                })

        # C-11: Validasi Toleransi Nominal PO vs PR (Membandingkan amount_untaxed / sebelum pajak)
        total_po_amount = sum(created_pos.mapped('amount_untaxed'))
        tolerance_pct = self.request_id.company_id.pr_po_tolerance or 5.0
        max_allowed_amount = self.request_id.amount_total * (1.0 + (tolerance_pct / 100.0))

        if total_po_amount > max_allowed_amount:
            raise ValidationError(_(
                "Total Purchase Order amount before tax (%(po_amt)s) exceeds the approved Purchase Request total (%(pr_amt)s) beyond the allowed tolerance of %(tol)s%% (Max: %(max_amt)s).",
                po_amt=total_po_amount,
                pr_amt=self.request_id.amount_total,
                tol=tolerance_pct,
                max_amt=max_allowed_amount
            ))

        # Update PR status ke done
        self.request_id.state = 'done'
        self.request_id._log_history(
            action='po_created',
            state_from='approved',
            state_to='done',
            comment=_("Created POs: %s") % ", ".join(created_pos.mapped('name')),
            level=self.request_id.required_level
        )

        if len(created_pos) == 1:
            return {
                'name': _('Purchase Order'),
                'view_mode': 'form',
                'res_model': 'purchase.order',
                'res_id': created_pos.id,
                'type': 'ir.actions.act_window',
            }
        else:
            return {
                'name': _('Purchase Orders'),
                'view_mode': 'tree,form',
                'res_model': 'purchase.order',
                'domain': [('id', 'in', created_pos.ids)],
                'type': 'ir.actions.act_window',
            }


class PurchaseRequestMakePoWizardLine(models.TransientModel):
    _name = 'purchase.request.make.po.wizard.line'
    _description = 'Purchase Request Make PO Wizard Line'

    wizard_id = fields.Many2one('purchase.request.make.po.wizard', string='Wizard', ondelete='cascade')
    selected = fields.Boolean(string='Select', default=True)
    request_line_id = fields.Many2one('purchase.request.line', string='Request Line', required=False)
    product_id = fields.Many2one('product.product', string='Product', required=False)
    name = fields.Text(string='Description', required=False)
    product_qty = fields.Float(string='Quantity', required=False)
    product_uom_id = fields.Many2one('uom.uom', string='UoM', required=False)
    estimated_unit_price = fields.Monetary(string='Unit Price', currency_field='currency_id', required=False)
    currency_id = fields.Many2one(related='wizard_id.request_id.currency_id', string='Currency')
    partner_id = fields.Many2one('res.partner', string='Vendor')
