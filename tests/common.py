# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo import fields


class PurchaseApprovalTestCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env.company
        cls.currency_idr = cls.env.ref('base.IDR', raise_if_not_found=False) or cls.company.currency_id

        # Departments
        cls.dept_production = cls.env['hr.department'].create({'name': 'Test Production'})
        cls.dept_sub_prod = cls.env['hr.department'].create({
            'name': 'Test Sub Production',
            'parent_id': cls.dept_production.id
        })
        cls.dept_warehouse = cls.env['hr.department'].create({'name': 'Test Warehouse'})
        cls.dept_purchasing = cls.env['hr.department'].create({'name': 'Test Purchasing'})

        # Groups
        cls.group_user = cls.env.ref('purchase_approval_management.group_pr_user')
        cls.group_spv = cls.env.ref('purchase_approval_management.group_pr_supervisor')
        cls.group_mgr = cls.env.ref('purchase_approval_management.group_pr_manager')
        cls.group_dir = cls.env.ref('purchase_approval_management.group_pr_director')
        cls.group_purch = cls.env.ref('purchase_approval_management.group_pr_purchasing')
        cls.group_audit = cls.env.ref('purchase_approval_management.group_pr_auditor')
        cls.group_admin = cls.env.ref('purchase_approval_management.group_pr_admin')

        # Users & Employees
        cls.user_requester = cls._create_user_with_employee('test_requester', cls.dept_production, [cls.group_user.id])
        cls.user_spv = cls._create_user_with_employee('test_spv', cls.dept_production, [cls.group_spv.id])
        cls.user_mgr = cls._create_user_with_employee('test_mgr', cls.dept_production, [cls.group_mgr.id])
        cls.user_dir = cls._create_user_with_employee('test_dir', cls.dept_production, [cls.group_dir.id])
        cls.user_purchasing = cls._create_user_with_employee('test_purchasing', cls.dept_purchasing, [cls.group_purch.id, cls.env.ref('purchase.group_purchase_user').id])
        cls.user_warehouse_spv = cls._create_user_with_employee('test_wh_spv', cls.dept_warehouse, [cls.group_spv.id])
        cls.user_auditor = cls._create_user_with_employee('test_auditor', cls.dept_production, [cls.group_audit.id])

        # Vendor & Products
        cls.vendor = cls.env['res.partner'].create({
            'name': 'Test Supplier Partner',
            'supplier_rank': 1,
        })
        cls.product_a = cls.env['product.product'].create({
            'name': 'Product Test A',
            'type': 'consu',
            'standard_price': 1000000.0,
        })

    @classmethod
    def _create_user_with_employee(cls, name, department, group_ids):
        user = cls.env['res.users'].create({
            'name': name,
            'login': f'{name}@test.com',
            'email': f'{name}@test.com',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id] + group_ids)],
        })
        cls.env['hr.employee'].create({
            'name': name,
            'user_id': user.id,
            'department_id': department.id if department else False,
        })
        return user

    def _create_pr(self, requester, total_target_amount, lines_count=1):
        unit_price = total_target_amount / lines_count
        lines = []
        for i in range(lines_count):
            lines.append((0, 0, {
                'product_id': self.product_a.id,
                'name': f'Line {i+1}',
                'product_qty': 1.0,
                'product_uom_id': self.product_a.uom_id.id,
                'estimated_unit_price': unit_price,
                'suggested_vendor_id': self.vendor.id,
            }))

        pr = self.env['purchase.request'].with_user(requester).create({
            'requester_id': requester.id,
            'department_id': requester.employee_id.department_id.id,
            'date_required': fields.Date.today(),
            'reason': 'Automated Test Purchase Request',
            'line_ids': lines,
        })
        return pr

