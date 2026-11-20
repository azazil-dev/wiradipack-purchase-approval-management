# -*- coding: utf-8 -*-
from odoo.tests.common import tagged
from odoo.exceptions import AccessError
from .common import PurchaseApprovalTestCommon


@tagged('post_install', '-at_install')
class TestSecurity(PurchaseApprovalTestCommon):

    def test_cross_department_visibility(self):
        """ UAT-09: Eko (Supervisor Gudang) tidak dapat melihat PR Departemen Produksi """
        pr = self._create_pr(self.user_requester, 3500000.0)
        pr.action_submit()

        # Baca via context user Eko (Gudang)
        prs_for_warehouse_spv = self.env['purchase.request'].with_user(self.user_warehouse_spv).search([('id', '=', pr.id)])
        self.assertFalse(prs_for_warehouse_spv, "Supervisor Gudang tidak boleh melihat PR Departemen Produksi.")

        # Siti (Supervisor Produksi) dapat melihat
        prs_for_prod_spv = self.env['purchase.request'].with_user(self.user_spv).search([('id', '=', pr.id)])
        self.assertTrue(prs_for_prod_spv, "Supervisor Produksi harus dapat melihat PR Departemennya.")

    def test_approval_rules_readonly_for_non_admin(self):
        """ UAT-15: Pengguna non-admin hanya bisa membaca master approval rules, tidak bisa membuat/mengedit """
        with self.assertRaises(AccessError):
            self.env['purchase.approval.rule'].with_user(self.user_spv).create({
                'name': 'Hacker Rule',
                'level': 'supervisor',
                'min_amount': 0.0,
                'group_id': self.group_spv.id,
            })

