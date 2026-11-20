# -*- coding: utf-8 -*-
from odoo.tests.common import tagged
from odoo.exceptions import UserError
from .common import PurchaseApprovalTestCommon


@tagged('post_install', '-at_install')
class TestAudit(PurchaseApprovalTestCommon):

    def test_audit_trail_and_history_immutable(self):
        """ UAT-13: Audit trail terisi otomatis saat create/write dan history tidak dapat diubah/dihapus """
        pr = self._create_pr(self.user_requester, 3500000.0)

        # Cek create audit log
        audit_logs = self.env['purchase.audit.log'].search([
            ('model_name', '=', 'purchase.request'),
            ('res_id', '=', pr.id),
            ('event', '=', 'create')
        ])
        self.assertTrue(audit_logs, "Audit log untuk operasi create harus terbentuk.")

        pr.action_submit()
        self.assertTrue(pr.history_ids)

        history_record = pr.history_ids[0]
        with self.assertRaises(UserError):
            history_record.write({'comment': 'Tampered comment'})

        with self.assertRaises(UserError):
            history_record.unlink()

