# -*- coding: utf-8 -*-
from odoo.tests.common import tagged
from odoo.exceptions import ValidationError
from .common import PurchaseApprovalTestCommon


@tagged('post_install', '-at_install')
class TestApprovalRules(PurchaseApprovalTestCommon):

    def test_rules_overlap_constraint(self):
        """ UAT-16: Constraint C-04 menolak rentang aturan approval yang tumpang tindih """
        with self.assertRaises(ValidationError):
            self.env['purchase.approval.rule'].create({
                'name': 'Overlapping Rule',
                'sequence': 50,
                'level': 'supervisor',
                'min_amount': 2000000.0,
                'max_amount': 7000000.0,
                'group_id': self.group_spv.id,
                'active': True,
                'company_id': self.company.id,
            })

