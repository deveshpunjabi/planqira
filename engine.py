"""
Planqira Deterministic Financial, Dependency DAG & Scenario Engine
Integer-Paise precision, half-up tax rounding, math.ceil step-tiers,
and real topological DAG dependency resolution.
"""

from collections import defaultdict, deque
import math
from typing import Any, Dict, List, Literal, Optional, Set, Tuple

PricingModel = Literal["FIXED", "PER_CAPITA", "STEP_TIERED"]
ApprovalState = Literal["ESTIMATED", "QUOTED", "APPROVED", "REJECTED", "REPLACED"]
PaymentStatus = Literal["UNPAID", "PARTIAL", "PAID"]


def calculate_tax_paise(subtotal_paise: int, tax_rate_bps: int) -> int:
    """
    Standard half-up financial integer rounding for tax in basis points.
    1800 bps = 18.00%. (subtotal * bps + 5000) // 10000 ensures exact rounding.
    Rejects negative inputs.
    """
    if tax_rate_bps < 0 or tax_rate_bps > 10000:
        raise ValueError(f"Tax rate basis points must be between 0 and 10000 (0-100%), got {tax_rate_bps}")
    if subtotal_paise < 0:
        raise ValueError(f"Subtotal cannot be negative, got {subtotal_paise}")
    if subtotal_paise == 0 or tax_rate_bps == 0:
        return 0
    return (subtotal_paise * tax_rate_bps + 5000) // 10000


def compute_line_item_paise(
    pricing_model: PricingModel,
    unit_cost_paise: int,
    guest_count: int,
    step_capacity: int = 1,
    tax_rate_bps: int = 0,
    is_tax_inclusive: bool = False,
) -> Dict[str, int]:
    """
    Calculates exact integer paise for a line item without floating-point drift.
    Strictly validates all inputs:
    - Guest count must be strictly positive (>= 1).
    - Unit cost must be non-negative (>= 0).
    - Step capacity must be strictly positive (>= 1) for tiered models.
    - Tax rate must be bounded between 0 and 10000 basis points.

    When is_tax_inclusive is True:
    - unit_cost_paise represents the gross unit price.
    - total_paise = quantity * unit_cost_paise (guaranteed exact to the paise with zero drift).
    - tax_paise is derived at the aggregation boundary: (total * bps + (10000+bps)//2) // (10000+bps).
    - subtotal_paise = total_paise - tax_paise.
    """
    if int(guest_count) <= 0:
        raise ValueError(f"Guest count must be strictly positive (>= 1), got {guest_count}")
    if int(unit_cost_paise) < 0:
        raise ValueError(f"Unit cost cannot be negative, got {unit_cost_paise}")
    if int(tax_rate_bps) < 0 or int(tax_rate_bps) > 10000:
        raise ValueError(f"Tax rate basis points must be between 0 and 10000 (0-100%), got {tax_rate_bps}")

    guests = int(guest_count)
    unit_paise = int(unit_cost_paise)

    if pricing_model == "FIXED":
        quantity = 1
    elif pricing_model == "PER_CAPITA":
        quantity = guests
    elif pricing_model == "STEP_TIERED":
        cap = int(step_capacity)
        if cap <= 0:
            raise ValueError(f"Step capacity must be strictly positive (>= 1), got {step_capacity}")
        quantity = math.ceil(guests / cap)
    else:
        raise ValueError(f"Unsupported pricing model: {pricing_model}. Must be FIXED, PER_CAPITA, or STEP_TIERED.")

    if is_tax_inclusive and tax_rate_bps > 0:
        total_paise = quantity * unit_paise
        tax_paise = (total_paise * tax_rate_bps + (10000 + tax_rate_bps) // 2) // (10000 + tax_rate_bps)
        subtotal_paise = total_paise - tax_paise
    else:
        subtotal_paise = quantity * unit_paise
        tax_paise = calculate_tax_paise(subtotal_paise, tax_rate_bps)
        total_paise = subtotal_paise + tax_paise

    return {
        "quantity": quantity,
        "unit_cost_paise": unit_paise,
        "subtotal_paise": subtotal_paise,
        "tax_paise": tax_paise,
        "total_paise": total_paise,
        "is_tax_inclusive": is_tax_inclusive,
    }


def evaluate_event_solvency(
    target_budget_paise: int,
    contingency_bps: int,  # 1000 = 10.00%
    line_items: List[Dict[str, Any]],
    guest_count: int,
    payments: Optional[List[Dict[str, Any]]] = None,
    vendor_commitments: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Evaluates complete budget ledger in integer paise.
    Strictly validates budget constraints.
    Separates Approval State (ESTIMATED/QUOTED/APPROVED/REJECTED/REPLACED) from Payment Tracking (PAID/PARTIAL/UNPAID).
    Authoritative cash paid is derived from the payments ledger.
    Never scales down items to fake 100% affordability; reports exact SURPLUS or DEFICIT.
    """
    if target_budget_paise < 0:
        raise ValueError(f"Target budget cannot be negative, got {target_budget_paise}")
    if contingency_bps < 0 or contingency_bps > 10000:
        raise ValueError(f"Contingency basis points must be between 0 and 10000, got {contingency_bps}")
    if guest_count <= 0:
        raise ValueError(f"Guest count must be strictly positive, got {guest_count}")

    contingency_paise = (target_budget_paise * contingency_bps + 5000) // 10000
    allocatable_paise = max(0, target_budget_paise - contingency_paise)

    by_approval = {"ESTIMATED": 0, "QUOTED": 0, "APPROVED": 0, "REJECTED": 0, "REPLACED": 0}
    by_payment = {"UNPAID": 0, "PARTIAL": 0, "PAID": 0}
    total_approved_commitments_paise = 0

    # 1. Authoritative payments derivation
    if payments is not None:
        total_paid_paise = sum(int(p.get("amount_paise", 0)) for p in payments)
        item_payments: Dict[str, int] = defaultdict(int)
        allocated_sum = 0
        for p in payments:
            amt = int(p.get("amount_paise", 0))
            b_id = p.get("budget_item_id")
            c_id = p.get("commitment_id")
            if b_id:
                item_payments[b_id] += amt
                allocated_sum += amt
            elif c_id:
                allocated_sum += amt
        unallocated_paid_paise = max(0, total_paid_paise - allocated_sum)
    else:
        total_paid_paise = sum(int(item.get("paid_amount_paise", 0)) for item in line_items)
        unallocated_paid_paise = 0
        item_payments = {item.get("id", ""): int(item.get("paid_amount_paise", 0)) for item in line_items}

    # 2. Deposit obligation derivation
    if vendor_commitments is not None:
        total_deposit_required_paise = sum(
            int(v.get("deposit_required_paise", 0))
            for v in vendor_commitments
            if v.get("approval_state") == "APPROVED"
        )
    else:
        total_deposit_required_paise = sum(
            int(item.get("deposit_required_paise", 0))
            for item in line_items
            if item.get("approval_state") == "APPROVED"
        )

    evaluated_items = []
    total_projected_paise = 0

    for item in line_items:
        is_incl = bool(item.get("is_tax_inclusive", False) or ("tax-inclusive" in str(item.get("notes", "")).lower()))
        calc = compute_line_item_paise(
            pricing_model=item["pricing_model"],
            unit_cost_paise=item["unit_cost_paise"],
            guest_count=guest_count,
            step_capacity=item.get("step_capacity", 1),
            tax_rate_bps=item.get("tax_rate_bps", 0),
            is_tax_inclusive=is_incl,
        )

        approval: ApprovalState = item.get("approval_state", "ESTIMATED")
        if approval in by_approval:
            by_approval[approval] += calc["total_paise"]

        # Only non-rejected and non-replaced items count towards projected spend
        if approval not in ("REJECTED", "REPLACED"):
            total_projected_paise += calc["total_paise"]

        if approval == "APPROVED":
            total_approved_commitments_paise += calc["total_paise"]

        # Item-specific cash paid from ledger or snapshot
        item_id = item.get("id")
        paid = item_payments.get(item_id, item.get("paid_amount_paise", 0)) if item_id else item.get("paid_amount_paise", 0)

        pay_status: PaymentStatus
        if paid >= calc["total_paise"] and calc["total_paise"] > 0:
            pay_status = "PAID"
        elif paid > 0:
            pay_status = "PARTIAL"
        else:
            pay_status = "UNPAID"

        by_payment[pay_status] += calc["total_paise"]

        evaluated_items.append({
            **item,
            **calc,
            "paid_amount_paise": paid,
            "calculated_payment_status": pay_status,
        })

    total_required_paise = contingency_paise + total_projected_paise
    variance_paise = target_budget_paise - total_required_paise
    solvency_status = "SOLVENT" if variance_paise >= 0 else "DEFICIT"
    total_outstanding_paise = max(0, total_approved_commitments_paise - total_paid_paise)
    projected_outstanding_paise = max(0, total_projected_paise - total_paid_paise)
    remaining_budget_paise = max(0, variance_paise)

    return {
        "target_budget_paise": target_budget_paise,
        "contingency_paise": contingency_paise,
        "allocatable_paise": allocatable_paise,
        "total_projected_paise": total_projected_paise,
        "total_approved_commitments_paise": total_approved_commitments_paise,
        "total_deposit_required_paise": total_deposit_required_paise,
        "total_required_paise": total_required_paise,
        "total_paid_paise": total_paid_paise,
        "unallocated_paid_paise": unallocated_paid_paise,
        "total_outstanding_paise": total_outstanding_paise,
        "projected_outstanding_paise": projected_outstanding_paise,
        "remaining_budget_paise": remaining_budget_paise,
        "variance_paise": variance_paise,
        "solvency_status": solvency_status,
        "breakdown_by_approval_paise": by_approval,
        "breakdown_by_payment_paise": by_payment,
        "items": evaluated_items,
    }


class DependencyDAG:
    """
    Real Directed Acyclic Graph (DAG) for event operational tasks and commitments.
    Tracks directed task dependencies (upstream -> downstream) and parameter triggers.
    """

    def __init__(self):
        self.adj: Dict[str, Set[str]] = defaultdict(set)  # u -> set(v) where v depends on u
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.param_subscribers: Dict[str, Set[str]] = defaultdict(set)  # param -> set(node_id)

    def add_node(
        self,
        node_id: str,
        node_type: Literal["TASK", "COMMITMENT"],
        title: str,
        depends_on_ids: Optional[List[str]] = None,
        trigger_params: Optional[List[str]] = None,
        status: str = "PENDING",
    ) -> None:
        self.nodes[node_id] = {
            "id": node_id,
            "type": node_type,
            "title": title,
            "status": status,
            "depends_on": depends_on_ids or [],
            "trigger_params": trigger_params or [],
        }

        if depends_on_ids:
            for parent_id in depends_on_ids:
                self.adj[parent_id].add(node_id)

        if trigger_params:
            for param in trigger_params:
                self.param_subscribers[param].add(node_id)

    def detect_cycles(self) -> bool:
        """Kahn's algorithm cycle check."""
        in_degree = {n: 0 for n in self.nodes}
        for u in self.adj:
            for v in self.adj[u]:
                if v in in_degree:
                    in_degree[v] += 1

        queue = deque([n for n, deg in in_degree.items() if deg == 0])
        visited_count = 0

        while queue:
            u = queue.popleft()
            visited_count += 1
            for v in self.adj.get(u, ()):
                if v in in_degree:
                    in_degree[v] -= 1
                    if in_degree[v] == 0:
                        queue.append(v)

        return visited_count != len(self.nodes)

    def propagate_invalidation(self, changed_params: List[str]) -> List[Dict[str, Any]]:
        """
        Traverses downstream dependencies when parameters change (e.g. guests, date, venue)
        and returns all affected tasks/commitments with reasons.
        """
        affected_node_ids: Set[str] = set()

        for param in changed_params:
            for node_id in self.param_subscribers.get(param, ()):
                affected_node_ids.add(node_id)

        # BFS downstream through the graph
        queue = deque(list(affected_node_ids))
        visited: Set[str] = set(affected_node_ids)

        while queue:
            curr = queue.popleft()
            for neighbor in self.adj.get(curr, ()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    affected_node_ids.add(neighbor)
                    queue.append(neighbor)

        results = []
        for nid in affected_node_ids:
            node = self.nodes.get(nid)
            if node:
                results.append({
                    "id": nid,
                    "title": node["title"],
                    "type": node["type"],
                    "previous_status": node["status"],
                    "new_action": "REOPEN_FOR_REVERIFICATION" if node["type"] == "TASK" else "FLAG_NEEDS_RECONFIRMATION",
                    "reason": f"Impacted by shift in parameters: {', '.join(changed_params)}",
                })

        return results


def simulate_scenario_impact(
    baseline_guests: int,
    new_guests: int,
    target_budget_paise: int,
    contingency_bps: int,
    line_items: List[Dict[str, Any]],
    dag: Optional[DependencyDAG] = None,
    baseline_date: Optional[str] = None,
    new_date: Optional[str] = None,
    baseline_setting: Optional[str] = None,
    new_setting: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Runs side-by-side Decision Impact comparison:
    1. Evaluates baseline vs. simulated solvency.
    2. Isolates exact paise delta for FIXED vs. PER_CAPITA vs. STEP_TIERED items.
    3. Runs DAG propagation across guests, date, and setting shifts.
    4. Produces concrete tradeoff statements without fabricated claims.
    """
    base_eval = evaluate_event_solvency(target_budget_paise, contingency_bps, line_items, baseline_guests)
    sim_eval = evaluate_event_solvency(target_budget_paise, contingency_bps, line_items, new_guests)

    cost_delta_paise = sim_eval["total_projected_paise"] - base_eval["total_projected_paise"]
    item_diffs = []

    for base_it, sim_it in zip(base_eval["items"], sim_eval["items"]):
        delta = sim_it["total_paise"] - base_it["total_paise"]
        item_diffs.append({
            "id": base_it.get("id"),
            "category": base_it.get("category", "General"),
            "name": base_it["name"],
            "pricing_model": base_it["pricing_model"],
            "base_quantity": base_it["quantity"],
            "new_quantity": sim_it["quantity"],
            "unit_cost_paise": base_it["unit_cost_paise"],
            "base_total_paise": base_it["total_paise"],
            "new_total_paise": sim_it["total_paise"],
            "delta_paise": delta,
            "approval_state": base_it.get("approval_state", "ESTIMATED"),
        })

    changed_params = []
    if new_guests != baseline_guests:
        changed_params.append("guests")
    if new_date and baseline_date and new_date != baseline_date:
        changed_params.append("date")
    if new_setting and baseline_setting and new_setting != baseline_setting:
        changed_params.append("setting")

    dag_impacts = []
    if dag and changed_params:
        dag_impacts = dag.propagate_invalidation(changed_params)

    # Concrete tradeoffs
    tradeoffs = []
    if new_guests > baseline_guests:
        tradeoffs.append(f"Guest expansion (+{new_guests - baseline_guests} guests) increases variable catering and tiered seating by ₹{cost_delta_paise/100:,.2f}.")
    elif new_guests < baseline_guests:
        tradeoffs.append(f"Guest reduction (-{baseline_guests - new_guests} guests) saves ₹{abs(cost_delta_paise)/100:,.2f} in per-capita catering while retaining fixed venue and production contracts.")

    if new_setting and baseline_setting and new_setting != baseline_setting:
        tradeoffs.append(f"Setting shift from {baseline_setting} to {new_setting} invalidates outdoor weather contingencies and requires venue floorplan reconfirmation.")

    if new_date and baseline_date and new_date != baseline_date:
        tradeoffs.append(f"Date shift from {baseline_date} to {new_date} requires reconfirming all vendor booking windows and calendar runbook cues.")

    return {
        "baseline_guests": baseline_guests,
        "new_guests": new_guests,
        "baseline_date": baseline_date,
        "new_date": new_date,
        "baseline_setting": baseline_setting,
        "new_setting": new_setting,
        "changed_params": changed_params,
        "baseline_projected_paise": base_eval["total_projected_paise"],
        "simulated_projected_paise": sim_eval["total_projected_paise"],
        "cost_delta_paise": cost_delta_paise,
        "baseline_solvency_status": base_eval["solvency_status"],
        "simulated_solvency_status": sim_eval["solvency_status"],
        "baseline_variance_paise": base_eval["variance_paise"],
        "simulated_variance_paise": sim_eval["variance_paise"],
        "contingency_paise": sim_eval["contingency_paise"],
        "remaining_budget_paise": sim_eval["remaining_budget_paise"],
        "item_diffs": item_diffs,
        "dag_impacts": dag_impacts,
        "tradeoffs": tradeoffs,
    }
