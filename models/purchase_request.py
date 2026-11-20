# -*- coding: utf-8 -*-
from datetime import date
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class PurchaseRequest(models.Model):
    _name = 'purchase.request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'purchase.audit.mixin']
    _description = 'Purchase Request'
    _order = 'id desc'

    name = fields.Char(
        string='Request Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        index=True
    )
    requester_id = fields.Many2one(
        'res.users',
        string='Requester',
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
        index=True
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        compute='_compute_department_id',
        store=True,
        readonly=False,
        index=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        index=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id
    )
    date_request = fields.Date(
        string='Request Date',
        required=True,
        default=fields.Date.context_today
    )
    date_required = fields.Date(
        string='Date Required',
        required=True,
        tracking=True
    )
    reason = fields.Text(string='Reason / Purpose', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'To Approve'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True, copy=False, index=True)

    line_ids = fields.One2many(
        'purchase.request.line',
        'request_id',
        string='Request Lines',
        copy=True
    )
    amount_total = fields.Monetary(
        string='Total',
        currency_field='currency_id',
        compute='_compute_amount_total',
        store=True,
        tracking=True
    )
    amount_total_formatted = fields.Char(
        string='Formatted Total',
        compute='_compute_amount_total_formatted'
    )
    amount_total_company = fields.Monetary(
        string='Total (Company Currency)',
        currency_field='company_currency_id',
        compute='_compute_amount_total_company',
        store=True
    )
    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Company Currency',
        readonly=True
    )
    required_level = fields.Selection([
        ('supervisor', 'Supervisor'),
        ('manager', 'Manager'),
        ('director', 'Director'),
    ], string='Required Level', compute='_compute_required_level', store=True, tracking=True)

    round_no = fields.Integer(string='Approval Round', default=1, copy=False)
    approval_line_ids = fields.One2many(
        'purchase.request.approval.line',
        'request_id',
        string='Approval Lines',
        copy=False
    )
    pending_approver_ids = fields.Many2many(
        'res.users',
        'purchase_request_pending_approver_rel',
        'request_id',
        'user_id',
        string='Pending Approvers',
        compute='_compute_pending_approver_ids',
        store=True
    )
    can_approve = fields.Boolean(
        string='Can Approve',
        compute='_compute_can_approve'
    )
    history_ids = fields.One2many(
        'purchase.approval.history',
        'request_id',
        string='Approval History',
        copy=False
    )
    purchase_order_ids = fields.One2many(
        'purchase.order',
        'purchase_request_id',
        string='Purchase Orders',
        copy=False
    )
    po_count = fields.Integer(
        string='Purchase Order Count',
        compute='_compute_po_count'
    )
    reject_reason = fields.Text(string='Reject Reason', copy=False, readonly=True)

    days_pending = fields.Integer(
        string='Days Pending',
        compute='_compute_pending_and_overdue',
        search='_search_days_pending'
    )
    is_overdue = fields.Boolean(
        string='Is Overdue',
        compute='_compute_pending_and_overdue',
        search='_search_is_overdue'
    )

    _sql_constraints = [
        (
            'check_name_company_unique',
            'UNIQUE(name, company_id)',
            'Purchase Request reference must be unique per company.'
        ),
    ]

    @api.depends('requester_id')
    def _compute_department_id(self):
        for req in self:
            employee = req.requester_id.employee_id if hasattr(req.requester_id, 'employee_id') else False
            req.department_id = employee.department_id.id if employee else False

    @api.depends('line_ids.subtotal')
    def _compute_amount_total(self):
        for req in self:
            req.amount_total = sum(req.line_ids.mapped('subtotal'))

    @api.depends('amount_total', 'currency_id')
    def _compute_amount_total_formatted(self):
        for req in self:
            symbol = req.currency_id.symbol or 'Rp'
            # Format pemisah ribuan dengan titik sesuai standar IDR (contoh: Rp 350.000.000)
            formatted = f"{req.amount_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            if formatted.endswith(',00'):
                formatted = formatted[:-3]
            req.amount_total_formatted = f"{symbol} {formatted}"

    @api.depends('amount_total', 'currency_id', 'date_request', 'company_id')
    def _compute_amount_total_company(self):
        for req in self:
            comp_currency = req.company_id.currency_id
            if req.currency_id and comp_currency and req.currency_id != comp_currency:
                req.amount_total_company = req.currency_id._convert(
                    req.amount_total,
                    comp_currency,
                    req.company_id,
                    req.date_request or fields.Date.today()
                )
            else:
                req.amount_total_company = req.amount_total

    @api.depends('amount_total_company', 'company_id')
    def _compute_required_level(self):
        for req in self:
            rules = self.env['purchase.approval.rule'].search([
                ('company_id', '=', req.company_id.id),
                ('active', '=', True)
            ], order='sequence asc, min_amount asc')
            level = False
            amount = req.amount_total_company
            for rule in rules:
                max_amt = rule.max_amount if (rule.max_amount and rule.max_amount > 0) else float('inf')
                if rule.min_amount <= amount <= max_amt:
                    level = rule.level
                    break
            req.required_level = level

    @api.depends('approval_line_ids.state', 'approval_line_ids.group_id', 'department_id', 'requester_id')
    def _compute_pending_approver_ids(self):
        admin_group = self.env.ref('purchase_approval_management.group_pr_admin', raise_if_not_found=False)

        for req in self:
            pending_line = req.approval_line_ids.filtered(lambda l: l.state == 'pending')
            if not pending_line:
                req.pending_approver_ids = [(5, 0, 0)]
                continue

            active_line = pending_line[0]
            group_users = active_line.group_id.users

            # Filter user != requester jika masih ada user lain di group tersebut
            eligible_users = group_users.filtered(lambda u: u.id != req.requester_id.id)
            if not eligible_users:
                # Fallback: jika hanya ada 1 user di database (misal saat testing/admin), izinkan group users
                eligible_users = group_users

            # Filter user belum pernah approve di level lain pada ronde ini (BR-04)
            previous_approvers = req.approval_line_ids.filtered(
                lambda l: l.state == 'approved' and l.approver_id
            ).mapped('approver_id')
            eligible_users = eligible_users.filtered(lambda u: u not in previous_approvers)

            # Filter departemen: Supervisor & Manager
            if active_line.level in ('supervisor', 'manager') and req.department_id:
                dept_ids = []
                dept = req.department_id
                while dept:
                    dept_ids.append(dept.id)
                    dept = dept.parent_id

                def is_in_dept(u):
                    emp = u.employee_id if hasattr(u, 'employee_id') else False
                    return bool(emp and emp.department_id.id in dept_ids)

                dept_filtered_users = eligible_users.filtered(is_in_dept)
                if dept_filtered_users:
                    eligible_users = dept_filtered_users
                elif req.department_id.manager_id and req.department_id.manager_id.user_id:
                    mgr_user = req.department_id.manager_id.user_id
                    if mgr_user in group_users:
                        eligible_users = mgr_user

            # Fallback pamungkas: jika tetap kosong (misal belum ada user manager terpisah),
            # masukkan Administrator sistem agar dokumen tidak macet
            if not eligible_users and admin_group and admin_group.users:
                eligible_users = admin_group.users

            req.pending_approver_ids = [(6, 0, eligible_users.ids)]

    def _compute_can_approve(self):
        current_user = self.env.user
        admin_group = self.env.ref('purchase_approval_management.group_pr_admin', raise_if_not_found=False)

        for req in self:
            if req.state != 'to_approve':
                req.can_approve = False
                continue

            pending_lines = req.approval_line_ids.filtered(lambda l: l.state == 'pending')
            if not pending_lines:
                req.can_approve = False
                continue

            active_line = pending_lines[0]
            group_users = active_line.group_id.users

            # Syarat 1: User merupakan anggota group level approval yang aktif
            is_member = current_user in group_users or (admin_group and current_user in admin_group.users) or self.env.is_admin()

            # Syarat 2: Pembuat tidak boleh approve sendiri
            is_requester = (current_user.id == req.requester_id.id) and not self.env.is_admin()

            if is_member and not is_requester:
                req.can_approve = True
            else:
                req.can_approve = False

    def _compute_po_count(self):
        for req in self:
            req.po_count = len(req.purchase_order_ids)

    def _compute_pending_and_overdue(self):
        today = fields.Date.today()
        for req in self:
            if req.state == 'to_approve' and req.date_request:
                days = (today - req.date_request).days
                req.days_pending = max(days, 0)
                sla_days = getattr(req.company_id, 'pr_escalation_days', 5) or 5
                req.is_overdue = days > sla_days
            else:
                req.days_pending = 0
                req.is_overdue = False

    def _search_days_pending(self, operator, value):
        # Fallback filter via python filtering on ID
        records = self.search([('state', '=', 'to_approve')])
        matching_ids = []
        for r in records:
            if operator == '>' and r.days_pending > value:
                matching_ids.append(r.id)
            elif operator == '>=' and r.days_pending >= value:
                matching_ids.append(r.id)
            elif operator == '<=' and r.days_pending <= value:
                matching_ids.append(r.id)
            elif operator == '<' and r.days_pending < value:
                matching_ids.append(r.id)
            elif operator in ('=', '==') and r.days_pending == value:
                matching_ids.append(r.id)
            elif operator in ('!=', '<>') and r.days_pending != value:
                matching_ids.append(r.id)
        return [('id', 'in', matching_ids)]

    def _search_is_overdue(self, operator, value):
        records = self.search([('state', '=', 'to_approve')])
        matching_ids = []
        target = bool(value)
        if operator in ('!=', '<>'):
            target = not target

        for r in records:
            if r.is_overdue == target:
                matching_ids.append(r.id)
        return [('id', 'in', matching_ids)]

    @api.constrains('date_required', 'date_request')
    def _check_dates(self):
        for req in self:
            if req.date_required and req.date_request and req.date_required < req.date_request:
                raise ValidationError(_("Date Required cannot be earlier than Request Date."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('purchase.request') or _('New')
        return super().create(vals_list)

    def write(self, vals):
        business_fields = {
            'requester_id', 'department_id', 'company_id', 'currency_id',
            'date_request', 'date_required', 'reason', 'line_ids'
        }
        for req in self:
            if req.state != 'draft' and any(f in vals for f in business_fields):
                if not self.env.context.get('allow_business_fields_write'):
                    raise UserError(_(
                        "You cannot modify business data (products, prices, dates, etc.) when the request is in '%s' status. Use 'Revise' instead.",
                        req.state
                    ))
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_non_draft(self):
        for req in self:
            if req.state != 'draft':
                raise UserError(_("You cannot delete a Purchase Request that is not in 'Draft' state."))

    # -------------------------------------------------------------------------
    # ACTION METHODS (WORKFLOW)
    # -------------------------------------------------------------------------

    def _log_history(self, action, state_from, state_to, comment=False, level=False):
        self.ensure_one()
        self.env['purchase.approval.history'].sudo().create({
            'request_id': self.id,
            'round_no': self.round_no,
            'level': level or self.required_level,
            'action': action,
            'actor_id': self.env.uid,
            'comment': comment,
            'state_from': state_from,
            'state_to': state_to,
            'amount_snapshot': self.amount_total,
        })

    def action_submit(self):
        level_order = ['supervisor', 'manager', 'director']

        for req in self:
            if req.state != 'draft':
                raise UserError(_("Only draft Purchase Requests can be submitted."))
            if not req.line_ids:
                raise ValidationError(_("Purchase Request must contain at least one line."))
            if req.amount_total <= 0:
                raise ValidationError(_("Total amount must be strictly greater than 0."))

            req._compute_amount_total_company()
            req._compute_required_level()

            if not req.required_level:
                raise UserError(_("No applicable approval rule found for amount %s.") % req.amount_total_company)

            mode = req.company_id.pr_approval_mode or 'highest_only'
            req.approval_line_ids.unlink()

            rule_model = self.env['purchase.approval.rule']
            approval_lines_data = []

            if mode == 'highest_only':
                target_rule = rule_model.search([
                    ('company_id', '=', req.company_id.id),
                    ('active', '=', True),
                    ('level', '=', req.required_level)
                ], limit=1)
                if not target_rule:
                    raise UserError(_("Approval rule for level '%s' not found.") % req.required_level)

                approval_lines_data.append({
                    'request_id': req.id,
                    'round_no': req.round_no,
                    'sequence': 10,
                    'level': target_rule.level,
                    'group_id': target_rule.group_id.id,
                    'state': 'pending',
                })
            else:  # Cumulative mode
                target_idx = level_order.index(req.required_level)
                needed_levels = level_order[:target_idx + 1]

                seq = 10
                for lvl in needed_levels:
                    lvl_rule = rule_model.search([
                        ('company_id', '=', req.company_id.id),
                        ('active', '=', True),
                        ('level', '=', lvl)
                    ], limit=1)
                    if not lvl_rule:
                        raise UserError(_("Approval rule for level '%s' not found.") % lvl)

                    approval_lines_data.append({
                        'request_id': req.id,
                        'round_no': req.round_no,
                        'sequence': seq,
                        'level': lvl_rule.level,
                        'group_id': lvl_rule.group_id.id,
                        'state': 'pending' if seq == 10 else 'waiting',
                    })
                    seq += 10

            self.env['purchase.request.approval.line'].sudo().create(approval_lines_data)
            req._compute_pending_approver_ids()

            # BR-03: Pastikan ada approver eligible untuk level yang aktif
            if not req.pending_approver_ids:
                admin_group = self.env.ref('purchase_approval_management.group_pr_admin', raise_if_not_found=False)
                if admin_group and admin_group.users:
                    req.pending_approver_ids = [(6, 0, admin_group.users.ids)]
                else:
                    raise UserError(_(
                        "Cannot submit request: No eligible approvers found for level '%s'."
                    ) % req.approval_line_ids[0].level)

            req.state = 'to_approve'
            req._notify_pending_approvers()
            req._log_history(
                action='submitted',
                state_from='draft',
                state_to='to_approve',
                level=req.approval_line_ids[0].level
            )
        return True

    def action_approve(self, comment=False):
        admin_group = self.env.ref('purchase_approval_management.group_pr_admin', raise_if_not_found=False)
        for req in self:
            if req.state != 'to_approve':
                raise UserError(_("Only requests in 'To Approve' status can be approved."))

            # Server-side validation hak akses
            is_admin_user = (admin_group and self.env.user in admin_group.users) or self.env.is_admin()
            if not req.can_approve and not is_admin_user and self.env.uid not in req.pending_approver_ids.ids:
                raise UserError(_("You are not authorized to approve this request at the current level."))

            pending_lines = req.approval_line_ids.filtered(lambda l: l.state == 'pending')
            if not pending_lines:
                raise UserError(_("No pending approval step found."))

            active_line = pending_lines[0]
            current_user = self.env.user

            # BR-03: Approver tidak boleh sama dengan requester
            if current_user.id == req.requester_id.id and not is_admin_user:
                raise UserError(_("Separation of duties: You cannot approve your own Purchase Request."))

            # BR-04: Approver belum approve di level lain pada ronde ini
            already_approved = req.approval_line_ids.filtered(
                lambda l: l.state == 'approved' and l.approver_id == current_user
            )
            if already_approved:
                raise UserError(_("You have already approved another level on this Purchase Request."))

            active_line.sudo().write({
                'state': 'approved',
                'approver_id': current_user.id,
                'action_date': fields.Datetime.now(),
                'comment': comment,
            })

            # Cek apakah masih ada level berikutnya (mode kumulatif)
            waiting_lines = req.approval_line_ids.filtered(lambda l: l.state == 'waiting')
            if waiting_lines:
                next_line = waiting_lines.sorted('sequence')[0]
                next_line.sudo().write({'state': 'pending'})
                req.sudo()._compute_pending_approver_ids()
                req._close_approval_activities()
                req._notify_pending_approvers()
                req._log_history(
                    action='approved',
                    state_from='to_approve',
                    state_to='to_approve',
                    comment=comment,
                    level=active_line.level
                )
            else:
                # Level terakhir selesai
                req.sudo().write({
                    'state': 'approved',
                    'pending_approver_ids': [(5, 0, 0)],
                })
                req._close_approval_activities()
                req._notify_approved()
                req._log_history(
                    action='approved',
                    state_from='to_approve',
                    state_to='approved',
                    comment=comment,
                    level=active_line.level
                )
        return True

    def action_reject(self, reason):
        for req in self:
            if req.state != 'to_approve':
                raise UserError(_("Only requests in 'To Approve' status can be rejected."))
            if not reason or not reason.strip():
                raise ValidationError(_("A reason is strictly required when rejecting a Purchase Request."))

            if not req.can_approve:
                raise UserError(_("You are not authorized to reject this request at the current level."))

            pending_lines = req.approval_line_ids.filtered(lambda l: l.state == 'pending')
            current_level = pending_lines[0].level if pending_lines else req.required_level

            if pending_lines:
                pending_lines[0].sudo().write({
                    'state': 'rejected',
                    'approver_id': self.env.uid,
                    'action_date': fields.Datetime.now(),
                    'comment': reason,
                })

            # Sisanya di-set skipped
            req.approval_line_ids.filtered(lambda l: l.state == 'waiting').sudo().write({'state': 'skipped'})

            req.sudo().write({
                'reject_reason': reason,
                'state': 'rejected'
            })
            req._compute_pending_approver_ids()
            req._close_approval_activities()
            req._notify_rejected()

            req._log_history(
                action='rejected',
                state_from='to_approve',
                state_to='rejected',
                comment=reason,
                level=current_level
            )
        return True

    def action_revise(self):
        for req in self:
            if req.state != 'rejected':
                raise UserError(_("Only rejected Purchase Requests can be revised."))
            if self.env.user.id != req.requester_id.id and not self.env.is_admin():
                raise UserError(_("Only the requester can revise this Purchase Request."))

            old_round = req.round_no
            req.with_context(allow_business_fields_write=True).write({
                'state': 'draft',
                'round_no': old_round + 1,
                'reject_reason': False,
            })

            req._log_history(
                action='revised',
                state_from='rejected',
                state_to='draft',
                comment=_("Revised to round %s") % req.round_no,
                level=req.required_level
            )
        return True

    def action_cancel(self, reason=False):
        for req in self:
            if req.state not in ('draft', 'to_approve'):
                raise UserError(_("Only requests in 'Draft' or 'To Approve' status can be cancelled."))
            if self.env.user.id != req.requester_id.id and not self.env.is_admin():
                raise UserError(_("Only the requester or an administrator can cancel this request."))

            old_state = req.state
            req.approval_line_ids.filtered(lambda l: l.state in ('pending', 'waiting')).sudo().write({'state': 'skipped'})
            req.state = 'cancel'
            req._compute_pending_approver_ids()

            # Tutup activity terbuka
            self._close_approval_activities()

            req._log_history(
                action='cancelled',
                state_from=old_state,
                state_to='cancel',
                comment=reason or _("Cancelled by %s") % self.env.user.name,
                level=req.required_level
            )
        return True

    # -------------------------------------------------------------------------
    # NOTIFICATION & AUTOMATION HELPERS
    # -------------------------------------------------------------------------

    def _notify_pending_approvers(self):
        act_type = self.env.ref('purchase_approval_management.mail_act_purchase_approval', raise_if_not_found=False)
        mail_template = self.env.ref('purchase_approval_management.mail_tmpl_pr_to_approve', raise_if_not_found=False)

        for req in self:
            for approver in req.pending_approver_ids:
                if act_type:
                    req.activity_schedule(
                        activity_type_id=act_type.id,
                        user_id=approver.id,
                        summary=_("Approval Needed for %s") % req.name,
                        note=_("Please review Purchase Request for %s") % req.amount_total_formatted
                    )
                if mail_template and approver.email:
                    mail_template.send_mail(req.id, force_send=False, email_values={'email_to': approver.email_formatted})

    def _notify_approved(self):
        tmpl = self.env.ref('purchase_approval_management.mail_tmpl_pr_approved', raise_if_not_found=False)
        purch_group = self.env.ref('purchase_approval_management.group_pr_purchasing', raise_if_not_found=False)
        todo_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)

        for req in self:
            if tmpl:
                tmpl.sudo().send_mail(req.id, force_send=False)
            if purch_group and todo_type:
                for user in purch_group.users:
                    req.sudo().activity_schedule(
                        activity_type_id=todo_type.id,
                        user_id=user.id,
                        summary=_("Create PO for %s") % req.name,
                        note=_("Purchase Request %s is approved and ready for PO creation.") % req.name
                    )

    def _notify_rejected(self):
        tmpl = self.env.ref('purchase_approval_management.mail_tmpl_pr_rejected', raise_if_not_found=False)
        for req in self:
            if tmpl:
                tmpl.sudo().send_mail(req.id, force_send=False)

    def _close_approval_activities(self):
        act_type = self.env.ref('purchase_approval_management.mail_act_purchase_approval', raise_if_not_found=False)
        for req in self:
            activities = req.sudo().activity_ids
            if act_type:
                activities = activities.filtered(lambda a: a.activity_type_id == act_type)
            activities.sudo().action_done()

    # -------------------------------------------------------------------------
    # CRON JOB IMPLEMENTATIONS
    # -------------------------------------------------------------------------

    @api.model
    def _cron_approval_reminder(self):
        today = fields.Date.today()
        pending_requests = self.search([('state', '=', 'to_approve')])
        reminder_tmpl = self.env.ref('purchase_approval_management.mail_tmpl_pr_reminder', raise_if_not_found=False)

        for req in pending_requests:
            sla_days = req.company_id.pr_reminder_days
            if not sla_days or sla_days <= 0 or not req.date_request:
                continue

            days = (today - req.date_request).days
            if days >= sla_days:
                for approver in req.pending_approver_ids:
                    if reminder_tmpl and approver.email:
                        reminder_tmpl.send_mail(req.id, force_send=False, email_values={'email_to': approver.email_formatted})
                req._log_history(
                    action='reminded',
                    state_from='to_approve',
                    state_to='to_approve',
                    comment=_("SLA reminder sent after %s days pending.") % days,
                    level=req.required_level
                )

    @api.model
    def _cron_approval_escalation(self):
        today = fields.Date.today()
        pending_requests = self.search([('state', '=', 'to_approve')])
        admin_group = self.env.ref('purchase_approval_management.group_pr_admin', raise_if_not_found=False)
        todo_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)

        for req in pending_requests:
            escalation_days = req.company_id.pr_escalation_days
            if not escalation_days or escalation_days <= 0 or not req.date_request:
                continue

            days = (today - req.date_request).days
            if days >= escalation_days:
                if admin_group and todo_type:
                    for admin in admin_group.users:
                        req.activity_schedule(
                            activity_type_id=todo_type.id,
                            user_id=admin.id,
                            summary=_("ESCALATION: Overdue PR %s") % req.name,
                            note=_("PR %s has been pending for %s days without action.") % (req.name, days)
                        )
                req._log_history(
                    action='escalated',
                    state_from='to_approve',
                    state_to='to_approve',
                    comment=_("PR escalated to administration after %s days pending.") % days,
                    level=req.required_level
                )

    @api.model
    def _cron_stale_draft_reminder(self):
        today = fields.Date.today()
        draft_requests = self.search([('state', '=', 'draft')])
        todo_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)

        for req in draft_requests:
            stale_days = req.company_id.pr_stale_draft_days or 30
            if not req.date_request:
                continue

            days = (today - req.date_request).days
            if days >= stale_days and todo_type:
                req.activity_schedule(
                    activity_type_id=todo_type.id,
                    user_id=req.requester_id.id,
                    summary=_("Reminder: Stale Draft PR %s") % req.name,
                    note=_("Your draft purchase request %s has not been submitted for %s days.") % (req.name, days)
                )
