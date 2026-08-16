# Copyright (c) 2026, SSSIHMS and contributors
# For license information, please see license.txt

"""Capital Purchase Requisition — the hospital's capital-purchase approval
chain, ported from HEM_Repository's requisition_workflow()/
can_act_on_requisition()/transition_requisition() line for line. Deliberately
**no Frappe Workflow doctype**: enforcement is this plain doctype plus a
single whitelisted transition() method, because the chain has rules a
generic Workflow doctype can't express on its own (raiser-exclusion that
survives an Administrator override, a department-eligible carve-out on two
specific steps, reason-required returns/rejects).

REQUISITION_WORKFLOW is the one fixed chain every requisition goes through,
named "capital" or not -- is_capital_requisition (derived from
Equipment Maintenance Settings' capital_purchase_threshold) is informational
only and never branches this chain, per the design plan.

Two kinds of step:

* "approval" -- Director / IPC / CPC / HEC / BoT. Any ONE role-holder acting
  once moves the requisition forward (a committee is not multi-member
  voting here -- matches the WordPress plugin's model). The raiser can
  NEVER act at an approval step on their own requisition, and an
  Administrator/System Manager does NOT bypass that exclusion -- the one
  place in this app admin override is deliberately withheld.
* "procedural" -- quotations / PO / stores receipt / issue to department /
  installation certification / finance payment. Two of these
  (quotations, installation_certified) are also department_eligible: the
  raising department can do its own quotations and certify its own
  installation, exactly mirroring HEM. Raiser-exclusion does not apply to
  procedural steps at all.

Content is locked past Draft (validate()'s _enforce_content_lock) -- once a
requisition leaves Draft, only transition() may change status/current_step/
history, and no field may change at all except through that one path.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from facility_management.equipment_maintenance.utils import get_user_department

#: The fixed chain. "draft" (before this list) and "completed" (after it) are
#: not represented here — they're markers, not actionable steps; see
#: STEP_KEYS/next_step_key() below. `role` is the single Role each step's
#: acting body corresponds to, per the design plan's explicit enumeration —
#: enumerated at build time, not improvised: Director, IPC Member,
#: CPC Member, HEC Member, BoT Member, Purchase, Stores, Finance, plus the
#: raising department itself (department_eligible, no dedicated Role for
#: that carve-out).
REQUISITION_WORKFLOW = [
	{"key": "director_approval", "label": "Director In-Principle Approval", "kind": "approval", "role": "Director"},
	{"key": "quotations", "label": "Quotations", "kind": "procedural", "role": "Purchase", "department_eligible": True},
	{"key": "ipc", "label": "IPC Negotiation", "kind": "approval", "role": "IPC Member"},
	{"key": "cpc", "label": "CPC Review", "kind": "approval", "role": "CPC Member"},
	{"key": "hec", "label": "HEC Review", "kind": "approval", "role": "HEC Member"},
	{"key": "bot", "label": "Board of Trustees Approval", "kind": "approval", "role": "BoT Member"},
	{"key": "po_issued", "label": "Purchase Issues PO", "kind": "procedural", "role": "Purchase", "department_eligible": False},
	{"key": "stores_received", "label": "Received In Stores", "kind": "procedural", "role": "Stores", "department_eligible": False},
	{"key": "issued_to_department", "label": "Issued To User Department", "kind": "procedural", "role": "Stores", "department_eligible": False},
	{"key": "installation_certified", "label": "Installation Certified", "kind": "procedural", "role": None, "department_eligible": True},
	{"key": "finance_payment", "label": "Finance Payment Sanction", "kind": "procedural", "role": "Finance", "department_eligible": False},
]

STEP_KEYS = [step["key"] for step in REQUISITION_WORKFLOW]

#: Fields locked once a requisition leaves Draft (_enforce_content_lock).
#: status/current_step/history are separately protected — see
#: _enforce_transition_only_fields — because they must change ONLY through
#: transition(), including while still in Draft (a caller must not be able
#: to hand-set status="Completed" via a plain save at any point). raised_by
#: is locked even more tightly still — see _enforce_raised_by_immutable —
#: it never changes after insert, not even during Draft, since it anchors
#: the approval-step raiser-exclusion check.
CONTENT_FIELDS = (
	"department",
	"title",
	"justification",
	"estimated_value",
	"linked_asset",
	"linked_ticket",
)

#: Actions transition() accepts.
ACTIONS = ("submit", "advance", "reject", "return", "resubmit", "withdraw")


def step_by_key(key):
	for step in REQUISITION_WORKFLOW:
		if step["key"] == key:
			return step
	return None


def next_step_key(current_key):
	"""The step after `current_key`, or "completed" past the last one."""
	if current_key == "draft":
		return STEP_KEYS[0]
	index = STEP_KEYS.index(current_key)
	if index == len(STEP_KEYS) - 1:
		return "completed"
	return STEP_KEYS[index + 1]


def _is_admin(user):
	return user == "Administrator" or "System Manager" in frappe.get_roles(user)


def can_act_on_step(user, requisition, step_key):
	"""Whether `user` may perform the forward action at `step_key` on this
	requisition right now. Does not cover reject/return/withdraw's own extra
	rules — see transition() — only "is this the right actor for this step".
	"""
	step = step_by_key(step_key)
	if not step:
		return False
	is_raiser = user == requisition.raised_by
	is_admin = _is_admin(user)
	if step["kind"] == "approval":
		# Raiser-exclusion is absolute at approval steps — an Administrator
		# who happens to also be the raiser does NOT get to bypass this,
		# the one deliberate exception to admin override in this app.
		if is_raiser:
			return False
		if is_admin:
			return True
		return step["role"] in frappe.get_roles(user)
	# procedural
	if step.get("department_eligible"):
		user_dept = get_user_department(user)
		if user_dept and user_dept == requisition.department:
			return True
	if is_admin:
		return True
	return bool(step["role"]) and step["role"] in frappe.get_roles(user)


def can_withdraw_requisition(user, requisition):
	"""A requisition may be withdrawn by its raiser (or an Administrator)
	only before real financial commitment (PO issuance) and only while it's
	still somewhere in the approval portion of the chain, not already
	terminal. Withdrawing after a PO has been issued would leave a vendor
	commitment with nothing tracking it — that has to be a separate,
	deliberate cancellation process this doctype doesn't model, not a
	same-button withdraw.
	"""
	if not (user == requisition.raised_by or _is_admin(user)):
		return False
	if requisition.status not in ("Draft", "Active", "Returned"):
		return False
	if requisition.current_step == "draft":
		return True
	if requisition.current_step not in STEP_KEYS:
		return False
	return STEP_KEYS.index(requisition.current_step) < STEP_KEYS.index("po_issued")


class CapitalPurchaseRequisition(Document):
	def before_insert(self):
		# New requisitions always start in Draft at the "draft" marker,
		# regardless of what a caller submits — same forced-initial-state
		# pattern as every other status-tracking doctype in this app.
		self.status = "Draft"
		self.current_step = "draft"
		# raised_by is always the creating user, never a caller-supplied
		# value — it's the anchor the raiser-exclusion check depends on, and
		# a writable raised_by would let anyone (Administrators included)
		# originate a requisition credited to someone else and then act on
		# it themselves at an approval step.
		self.raised_by = frappe.session.user

	def validate(self):
		if self.is_new():
			self._compute_is_capital_requisition()
		else:
			self._enforce_raised_by_immutable()
			self._enforce_content_lock()
			self._enforce_transition_only_fields()

	def _compute_is_capital_requisition(self):
		threshold = frappe.db.get_single_value(
			"Equipment Maintenance Settings", "capital_purchase_threshold"
		)
		self.is_capital_requisition = bool(threshold and self.estimated_value and self.estimated_value >= threshold)

	def _enforce_raised_by_immutable(self):
		# raised_by is set once, at creation, from the session user and never
		# changes again — not even while still in Draft. It's the anchor the
		# raiser-exclusion check at approval steps relies on; a raised_by
		# that could be edited after insert would let anyone re-point an
		# existing requisition away from themselves and then act on it at an
		# approval step.
		before = self.get_doc_before_save()
		if before and self.raised_by != before.raised_by:
			frappe.throw(
				_("raised_by cannot be changed once a requisition is created."),
				title=_("Capital Purchase Requisition"),
			)

	def _enforce_content_lock(self):
		before = self.get_doc_before_save()
		if not before or before.status == "Draft":
			return  # still in Draft — content is editable up to the point it leaves Draft
		for fieldname in CONTENT_FIELDS:
			if self.get(fieldname) != before.get(fieldname):
				frappe.throw(
					_("This requisition has left Draft and its content can no longer be edited."),
					title=_("Capital Purchase Requisition"),
				)

	def _enforce_transition_only_fields(self):
		# status/current_step/history may change ONLY via transition() (which
		# sets self.flags.via_transition before calling save()) — never via a
		# plain .save() call, even from Draft, and even by an Administrator.
		# history's JSON read_only:1 is a UI property only; without this
		# check a caller with plain write access could forge or erase
		# approval-trail entries through an ordinary document save.
		if self.flags.get("via_transition"):
			return
		before = self.get_doc_before_save()
		if not before:
			return
		if self.status != before.status or self.current_step != before.current_step:
			frappe.throw(
				_("status and current_step can only change through the transition() action, not a direct save."),
				title=_("Capital Purchase Requisition"),
			)
		if self._history_as_rows(self) != self._history_as_rows(before):
			frappe.throw(
				_("history can only change through the transition() action, not a direct save."),
				title=_("Capital Purchase Requisition"),
			)

	@staticmethod
	def _history_as_rows(doc):
		return [
			(row.step, row.action, row.actor, str(row.timestamp), row.reason)
			for row in (doc.history or [])
		]

	def _log(self, step, action, user, reason=None):
		self.append(
			"history",
			{
				"step": step,
				"action": action,
				"actor": user,
				"timestamp": now_datetime(),
				"reason": reason,
			},
		)

	def _save_via_transition(self):
		self.flags.via_transition = True
		self.save(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def transition(name, action, reason=None):
	"""The only way a Capital Purchase Requisition moves. Mirrors
	transition_requisition()/can_act_on_requisition() line for line: chain
	order, the approval/procedural raiser-exclusion carve-out, and
	reason-required on return/reject are all enforced here, not just hinted
	at in the UI.
	"""
	if action not in ACTIONS:
		frappe.throw(_("Unknown action {0}.").format(action), title=_("Capital Purchase Requisition"))

	doc = frappe.get_doc("Capital Purchase Requisition", name)
	doc.check_permission("write")
	user = frappe.session.user

	if action == "submit":
		if doc.status != "Draft":
			frappe.throw(_("Only a Draft requisition can be submitted."), title=_("Capital Purchase Requisition"))
		if not (user == doc.raised_by or _is_admin(user)):
			frappe.throw(
				_("Only the raiser (or an Administrator) can submit this requisition."),
				title=_("Capital Purchase Requisition"),
			)
		doc._log("draft", "submit", user)
		doc.current_step = STEP_KEYS[0]
		doc.status = "Active"

	elif action == "resubmit":
		if doc.status != "Returned":
			frappe.throw(_("Only a Returned requisition can be resubmitted."), title=_("Capital Purchase Requisition"))
		if not (user == doc.raised_by or _is_admin(user)):
			frappe.throw(
				_("Only the raiser (or an Administrator) can resubmit this requisition."),
				title=_("Capital Purchase Requisition"),
			)
		doc._log(doc.current_step, "resubmit", user)
		doc.status = "Active"

	elif action == "withdraw":
		if not can_withdraw_requisition(user, doc):
			frappe.throw(
				_("This requisition cannot be withdrawn now."), title=_("Capital Purchase Requisition")
			)
		doc._log(doc.current_step, "withdraw", user, reason)
		doc.status = "Withdrawn"

	elif action == "advance":
		if doc.status != "Active":
			frappe.throw(_("Only an Active requisition can be advanced."), title=_("Capital Purchase Requisition"))
		if not can_act_on_step(user, doc, doc.current_step):
			frappe.throw(
				_("You are not the actor for the {0} step.").format(doc.current_step),
				title=_("Capital Purchase Requisition"),
			)
		doc._log(doc.current_step, "advance", user)
		next_key = next_step_key(doc.current_step)
		doc.current_step = next_key
		if next_key == "completed":
			doc.status = "Completed"

	elif action == "reject":
		step = step_by_key(doc.current_step)
		if doc.status != "Active" or not step or step["kind"] != "approval":
			frappe.throw(
				_("A requisition can only be rejected at an approval step."), title=_("Capital Purchase Requisition")
			)
		if not can_act_on_step(user, doc, doc.current_step):
			frappe.throw(
				_("You are not the actor for the {0} step.").format(doc.current_step),
				title=_("Capital Purchase Requisition"),
			)
		if not reason:
			frappe.throw(_("A reason is required to reject a requisition."), title=_("Capital Purchase Requisition"))
		doc._log(doc.current_step, "reject", user, reason)
		doc.status = "Rejected"

	elif action == "return":
		if doc.status != "Active":
			frappe.throw(_("Only an Active requisition can be returned."), title=_("Capital Purchase Requisition"))
		if not can_act_on_step(user, doc, doc.current_step):
			frappe.throw(
				_("You are not the actor for the {0} step.").format(doc.current_step),
				title=_("Capital Purchase Requisition"),
			)
		if not reason:
			frappe.throw(
				_("A reason is required to return a requisition for clarification."),
				title=_("Capital Purchase Requisition"),
			)
		doc._log(doc.current_step, "return", user, reason)
		doc.status = "Returned"
		# current_step deliberately unchanged — resubmit re-enters the SAME
		# step for the SAME actor to reconsider, rather than restarting the
		# whole chain from Draft.

	doc._save_via_transition()
	return {"name": doc.name, "status": doc.status, "current_step": doc.current_step}
