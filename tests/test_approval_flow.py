# -*- coding: utf-8 -*-
from odoo.tests.common import tagged
from odoo.exceptions import UserError, ValidationError
from .common import PurchaseApprovalTestCommon


@tagged('post_install', '-at_install')
class TestPurchaseApprovalFlow(PurchaseApprovalTestCommon):

    def test_01_small_pr_supervisor_approval(self):
        """ UAT-01: PR kecil (Rp3.500.000) disetujui Supervisor -> status approved """
        pr = self._create_pr(self.user_requester, 3500000.0)
        self.assertEqual(pr.state, 'draft')
        self.assertEqual(pr.amount_total, 3500000.0)
        self.assertEqual(pr.required_level, 'supervisor')

        pr.action_submit()
        self.assertEqual(pr.state, 'to_approve')
        self.assertIn(self.user_spv.id, pr.pending_approver_ids.ids)
        self.assertNotIn(self.user_requester.id, pr.pending_approver_ids.ids)

        pr.with_user(self.user_spv).action_approve(comment="Approved by Supervisor")
        self.assertEqual(pr.state, 'approved')
        self.assertEqual(len(pr.history_ids), 2)  # submitted, approved

    def test_02_medium_pr_manager_approval(self):
        """ UAT-02: PR menengah (Rp25.000.000) hanya Manager yang berhak approve """
        pr = self._create_pr(self.user_requester, 2500000.0 * 10)  # 25jt
        pr.action_submit()

        self.assertEqual(pr.required_level, 'manager')
        self.assertIn(self.user_mgr.id, pr.pending_approver_ids.ids)
        self.assertNotIn(self.user_spv.id, pr.pending_approver_ids.ids)

        with self.assertRaises(UserError):
            pr.with_user(self.user_spv).action_approve()

        pr.with_user(self.user_mgr).action_approve()
        self.assertEqual(pr.state, 'approved')

    def test_03_large_pr_director_approval(self):
        """ UAT-03: PR besar (Rp75.000.000) hanya Director yang berhak approve """
        pr = self._create_pr(self.user_requester, 75000000.0)
        pr.action_submit()

        self.assertEqual(pr.required_level, 'director')
        self.assertIn(self.user_dir.id, pr.pending_approver_ids.ids)
        self.assertNotIn(self.user_mgr.id, pr.pending_approver_ids.ids)

        with self.assertRaises(UserError):
            pr.with_user(self.user_mgr).action_approve()

        pr.with_user(self.user_dir).action_approve()
        self.assertEqual(pr.state, 'approved')

    def test_04_boundary_values(self):
        """ UAT-04: Pengujian nilai batas nominal """
        # 4.999.999 -> supervisor
        pr1 = self._create_pr(self.user_requester, 4999999.0)
        self.assertEqual(pr1.required_level, 'supervisor')

        # 5.000.000 -> manager
        pr2 = self._create_pr(self.user_requester, 5000000.0)
        self.assertEqual(pr2.required_level, 'manager')

        # 50.000.000 -> manager
        pr3 = self._create_pr(self.user_requester, 50000000.0)
        self.assertEqual(pr3.required_level, 'manager')

        # 50.000.001 -> director
        pr4 = self._create_pr(self.user_requester, 50000001.0)
        self.assertEqual(pr4.required_level, 'director')

    def test_05_rejection_requires_reason(self):
        """ UAT-05: Penolakan wajib disertai alasan """
        pr = self._create_pr(self.user_requester, 3500000.0)
        pr.action_submit()

        with self.assertRaises(ValidationError):
            pr.with_user(self.user_spv).action_reject(reason=" ")

        pr.with_user(self.user_spv).action_reject(reason="Budget exceeded")
        self.assertEqual(pr.state, 'rejected')
        self.assertEqual(pr.reject_reason, "Budget exceeded")

    def test_06_revise_workflow(self):
        """ UAT-06: Revise dan ajukan ulang menambah round_no dan reset draft """
        pr = self._create_pr(self.user_requester, 3500000.0)
        pr.action_submit()
        pr.with_user(self.user_spv).action_reject(reason="Revise qty")

        pr.with_user(self.user_requester).action_revise()
        self.assertEqual(pr.state, 'draft')
        self.assertEqual(pr.round_no, 2)

    def test_07_separation_of_duties_self_approval(self):
        """ UAT-07: Requester tidak boleh menyetujui PR miliknya sendiri """
        # Supervisor membuat PR sendiri
        pr = self._create_pr(self.user_spv, 3500000.0)

        # Karena dia requester tunggal di departemen tanpa spv lain, submit diblok jika tidak ada approver
        # Tambah spv lain agar bisa submit
        other_spv = self._create_user_with_employee('other_spv', self.dept_production, [self.group_spv.id])
        pr.action_submit()

        self.assertNotIn(self.user_spv.id, pr.pending_approver_ids.ids)
        with self.assertRaises(UserError):
            pr.with_user(self.user_spv).action_approve()

    def test_08_field_lock_after_submit(self):
        """ UAT-08: Field bisnis terkunci setelah submit """
        pr = self._create_pr(self.user_requester, 3500000.0)
        pr.action_submit()

        with self.assertRaises(UserError):
            pr.write({'reason': 'Hacker changed reason'})

    def test_10_make_po_from_approved_pr(self):
        """ UAT-10 & UAT-11: Membuat PO dari PR approved dan validasi enforcement """
        pr = self._create_pr(self.user_requester, 3500000.0)
        pr.action_submit()
        pr.with_user(self.user_spv).action_approve()

        wizard = self.env['purchase.request.make.po.wizard'].with_user(self.user_purchasing).with_context(
            active_id=pr.id
        ).create({})
        wizard.action_create_po()

        self.assertEqual(pr.state, 'done')
        self.assertEqual(len(pr.purchase_order_ids), 1)

        po = pr.purchase_order_ids[0]
        self.assertEqual(po.purchase_request_id.id, pr.id)

        # Test PO confirmation
        po.with_user(self.user_purchasing).button_confirm()
        self.assertIn(po.state, ('purchase', 'done'))

    def test_11_po_enforcement_blocks_manual_po(self):
        """ UAT-11: PO manual tanpa PR diblokir saat enforcement aktif """
        self.company.enforce_pr_on_po = True
        po = self.env['purchase.order'].with_user(self.user_purchasing).create({
            'partner_id': self.vendor.id,
            'order_line': [(0, 0, {
                'product_id': self.product_a.id,
                'name': 'Test Item',
                'product_qty': 1.0,
                'product_uom': self.product_a.uom_id.id,
                'price_unit': 1000000.0,
                'date_planned': fields.Date.today(),
            })],
        })

        with self.assertRaises(UserError):
            po.button_confirm()

    def test_19_cumulative_mode(self):
        """ UAT-19: Mode kumulatif memerlukan persetujuan berurutan dari Supervisor, Manager, lalu Director """
        self.company.pr_approval_mode = 'cumulative'
        pr = self._create_pr(self.user_requester, 75000000.0)
        pr.action_submit()

        self.assertEqual(len(pr.approval_line_ids), 3)

        # Level 1: Supervisor pending
        self.assertIn(self.user_spv.id, pr.pending_approver_ids.ids)
        pr.with_user(self.user_spv).action_approve()
        self.assertEqual(pr.state, 'to_approve')

        # Level 2: Manager pending
        self.assertIn(self.user_mgr.id, pr.pending_approver_ids.ids)
        pr.with_user(self.user_mgr).action_approve()
        self.assertEqual(pr.state, 'to_approve')

        # Level 3: Director pending
        self.assertIn(self.user_dir.id, pr.pending_approver_ids.ids)
        pr.with_user(self.user_dir).action_approve()
        self.assertEqual(pr.state, 'approved')

