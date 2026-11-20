# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.http import request


class PurchaseAuditMixin(models.AbstractModel):
    _name = 'purchase.audit.mixin'
    _description = 'Purchase Audit Mixin'

    def _get_client_ip(self):
        try:
            if request and hasattr(request, 'httprequest'):
                return request.httprequest.environ.get('HTTP_X_FORWARDED_FOR', request.httprequest.remote_addr)
        except Exception:
            pass
        return False

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        ip = self._get_client_ip()
        audit_log_obj = self.env['purchase.audit.log'].sudo()
        logs_to_create = []
        for record in records:
            display_name = record.display_name if hasattr(record, 'display_name') else str(record.id)
            logs_to_create.append({
                'model_name': self._name,
                'res_id': record.id,
                'record_name': display_name,
                'event': 'create',
                'field_name': False,
                'old_value': False,
                'new_value': False,
                'user_id': self.env.uid,
                'ip_address': ip,
            })
        if logs_to_create:
            audit_log_obj.create(logs_to_create)
        return records

    def write(self, vals):
        # Ignore tracking/technical only write updates
        ignored_fields = {'__last_update', 'write_date', 'write_uid'}
        tracked_keys = [k for k in vals.keys() if k not in ignored_fields and k in self._fields]

        old_values = {}
        if tracked_keys:
            for record in self:
                old_values[record.id] = {field: getattr(record, field) for field in tracked_keys}

        res = super().write(vals)

        if tracked_keys:
            ip = self._get_client_ip()
            audit_log_obj = self.env['purchase.audit.log'].sudo()
            logs_to_create = []

            for record in self:
                display_name = record.display_name if hasattr(record, 'display_name') else str(record.id)
                rec_old = old_values.get(record.id, {})
                for field in tracked_keys:
                    old_val = rec_old.get(field)
                    new_val = getattr(record, field)
                    if old_val != new_val:
                        logs_to_create.append({
                            'model_name': self._name,
                            'res_id': record.id,
                            'record_name': display_name,
                            'event': 'write',
                            'field_name': field,
                            'old_value': str(old_val) if old_val is not None else '',
                            'new_value': str(new_val) if new_val is not None else '',
                            'user_id': self.env.uid,
                            'ip_address': ip,
                        })
            if logs_to_create:
                audit_log_obj.create(logs_to_create)

        return res

    def unlink(self):
        ip = self._get_client_ip()
        audit_log_obj = self.env['purchase.audit.log'].sudo()
        logs_to_create = []
        for record in self:
            display_name = record.display_name if hasattr(record, 'display_name') else str(record.id)
            logs_to_create.append({
                'model_name': self._name,
                'res_id': record.id,
                'record_name': display_name,
                'event': 'unlink',
                'field_name': False,
                'old_value': False,
                'new_value': False,
                'user_id': self.env.uid,
                'ip_address': ip,
            })
        if logs_to_create:
            audit_log_obj.create(logs_to_create)
        return super().unlink()

