"""
Planqira SQLite Persistence Engine (planqira.db)
ACID-compliant relational storage with schema migrations,
foreign keys, payment ledgers, incident logging, and audit trail.
"""

import json
import time
import uuid
from datetime import date
from typing import Any

# Preserve the public database entry points used by the app and existing integrations.
from database_setup import get_connection as get_connection
from database_setup import get_db_path as get_db_path
from database_setup import init_db as init_db
from engine import build_task_dag, compute_line_item_paise
from event_creation import create_event as create_event


def get_event_by_id(event_id: str, db_path: str | None = None) -> dict[str, Any] | None:
    target_path = db_path or get_db_path()
    with get_connection(target_path) as conn:
        evt_row = conn.execute("SELECT * FROM events WHERE id = ?;", (event_id,)).fetchone()
        if not evt_row:
            return None
        event = dict(evt_row)
        if "preferences_json" in event and event["preferences_json"]:
            try:
                event["preferences"] = json.loads(event["preferences_json"])
            except (json.JSONDecodeError, TypeError):
                event["preferences"] = {}

        sc_row = conn.execute(
            "SELECT * FROM scenarios WHERE event_id = ? AND status = 'ACTIVE';", (event_id,)
        ).fetchone()
        scenario = dict(sc_row) if sc_row else None
        scenario_id = scenario["id"] if scenario else None

        items = []
        if scenario_id:
            i_rows = conn.execute(
                "SELECT * FROM budget_items WHERE scenario_id = ?;", (scenario_id,)
            ).fetchall()
            items = [dict(r) for r in i_rows]

        v_rows = conn.execute(
            "SELECT * FROM vendor_commitments WHERE event_id = ?;", (event_id,)
        ).fetchall()
        vendors = [dict(r) for r in v_rows]

        t_rows = conn.execute(
            "SELECT * FROM tasks WHERE event_id = ? ORDER BY due_date ASC;", (event_id,)
        ).fetchall()
        tasks = [dict(r) for r in t_rows]

        dep_rows = conn.execute(
            """SELECT d.* FROM task_dependencies d
                                JOIN tasks t ON t.id = d.parent_task_id WHERE t.event_id = ?;""",
            (event_id,),
        ).fetchall()
        dependencies = [(r["parent_task_id"], r["child_task_id"]) for r in dep_rows]

        rb_rows = conn.execute(
            "SELECT * FROM runbook_cues WHERE event_id = ?;", (event_id,)
        ).fetchall()
        runbook = [dict(r) for r in rb_rows]

        th_rows = conn.execute("SELECT * FROM themes WHERE event_id = ?;", (event_id,)).fetchall()
        themes = []
        for r in th_rows:
            d = dict(r)
            d["palette_hex"] = (
                json.loads(d["palette_hex"])
                if isinstance(d["palette_hex"], str)
                else d["palette_hex"]
            )
            themes.append(d)

        pay_rows = conn.execute(
            """SELECT p.*, COALESCE(b.obligation_id, p.budget_item_id) AS obligation_id
                                FROM payments p LEFT JOIN budget_items b ON b.id = p.budget_item_id
                                WHERE p.event_id = ? ORDER BY p.paid_at DESC;""",
            (event_id,),
        ).fetchall()
        payments = [dict(r) for r in pay_rows]

        inc_rows = conn.execute(
            "SELECT * FROM incidents WHERE event_id = ? ORDER BY created_at DESC;", (event_id,)
        ).fetchall()
        incidents = [dict(r) for r in inc_rows]

        log_rows = conn.execute(
            "SELECT * FROM audit_logs WHERE event_id = ? ORDER BY id DESC LIMIT 30;", (event_id,)
        ).fetchall()
        logs = [dict(r) for r in log_rows]

        sc_history_rows = conn.execute(
            "SELECT * FROM scenarios WHERE event_id = ? ORDER BY version ASC;", (event_id,)
        ).fetchall()
        scenarios_history = [dict(r) for r in sc_history_rows]

        return {
            "event": event,
            "active_scenario": scenario,
            "scenarios_history": scenarios_history,
            "budget_items": items,
            "vendors": vendors,
            "tasks": tasks,
            "dependencies": dependencies,
            "runbook": runbook,
            "themes": themes,
            "payments": payments,
            "incidents": incidents,
            "audit_logs": logs,
        }


def list_events(db_path: str | None = None) -> list[dict[str, Any]]:
    target_path = db_path or get_db_path()
    with get_connection(target_path) as conn:
        rows = conn.execute("SELECT * FROM events ORDER BY created_at DESC;").fetchall()
        return [dict(r) for r in rows]


def _copy_budget_items(conn, event_id, version, scenario_id, items):
    """Copy obligations into a revision; cash remains in the immutable payment ledger."""
    rows = []
    for index, item in enumerate(items, start=1):
        rows.append(
            (
                f"item-{event_id}-v{version}-{index}-{uuid.uuid4().hex[:6]}",
                scenario_id,
                item["category"],
                item["name"],
                item["pricing_model"],
                item["unit_cost_paise"],
                item.get("step_capacity", 1),
                item.get("tax_rate_bps", 0),
                item.get("approval_state", "ESTIMATED"),
                item.get("deposit_required_paise", 0),
                0,
                item.get("deposit_due_date"),
                item.get("superseded_by_id"),
                item.get("notes"),
                int(item.get("is_tax_inclusive", 0)),
                item.get("obligation_id") or item["id"],
            )
        )
    conn.executemany(
        """
        INSERT INTO budget_items (id, scenario_id, category, name, pricing_model, unit_cost_paise,
            step_capacity, tax_rate_bps, approval_state, deposit_required_paise, paid_amount_paise,
            deposit_due_date, superseded_by_id, notes, is_tax_inclusive, obligation_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """,
        rows,
    )


def _shift_task_dates(conn, event_id, old_date, new_date):
    """Move planned deadlines with the event without deleting task identity or history."""
    shift = (date.fromisoformat(new_date) - date.fromisoformat(old_date)).days
    if shift:
        conn.execute(
            """UPDATE tasks SET due_date = date(due_date, ?)
               WHERE event_id = ? AND due_date IS NOT NULL;""",
            (f"{shift:+d} days", event_id),
        )


def commit_scenario_version(
    event_id: str,
    new_guests: int,
    new_budget_items: list[dict[str, Any]] | None = None,
    note: str = "Scenario proposal",
    base_version: int | None = None,
    new_setting: str | None = None,
    setting: str | None = None,
    new_date: str | None = None,
    invalidated_task_ids: list[str] | None = None,
    db_path: str | None = None,
) -> dict[str, Any]:
    """
    Transactionally creates a new immutable scenario version, verifies baseline version,
    persists affected tasks as NEEDS_REVIEW, and writes an audit log.
    """
    target_path = db_path or get_db_path()
    now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    with get_connection(target_path) as conn:
        evt = conn.execute("SELECT * FROM events WHERE id = ?;", (event_id,)).fetchone()
        if not evt:
            raise ValueError(f"Event {event_id} not found")

        old_version = evt["active_scenario_version"]
        if base_version is not None and base_version != old_version:
            raise ValueError(
                f"Stale proposal rejected: Base version v{base_version} does not match current active version v{old_version}."
            )

        new_version = old_version + 1
        new_sc_id = f"sc-{event_id}-v{new_version}"
        chosen_setting = (new_setting or setting or evt["setting"]).lower()

        # Determine budget items authoritatively from the active scenario (P0: prevent client cost forgery)
        active_sc = conn.execute(
            "SELECT * FROM scenarios WHERE event_id = ? AND status = 'ACTIVE';", (event_id,)
        ).fetchone()
        if not active_sc:
            raise ValueError(f"No active scenario found for event {event_id}")

        prev_rows = conn.execute(
            "SELECT * FROM budget_items WHERE scenario_id = ?;", (active_sc["id"],)
        ).fetchall()
        items_to_insert = [dict(r) for r in prev_rows]

        # Archive old active scenario
        conn.execute(
            "UPDATE scenarios SET status = 'ARCHIVED' WHERE event_id = ? AND status = 'ACTIVE';",
            (event_id,),
        )

        # Create new scenario with event_date snapshot
        scenario_date = new_date or evt["event_date"]
        conn.execute(
            """
            INSERT INTO scenarios (id, event_id, version, name, guest_count, target_budget_paise, setting, event_date, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?);
        """,
            (
                new_sc_id,
                event_id,
                new_version,
                f"Scenario v{new_version} ({note})",
                new_guests,
                evt["target_budget_paise"],
                chosen_setting,
                scenario_date,
                now_str,
            ),
        )

        _copy_budget_items(conn, event_id, new_version, new_sc_id, items_to_insert)
        _shift_task_dates(conn, event_id, evt["event_date"], scenario_date)

        # Authoritatively evaluate shifted parameters and DAG task invalidations
        changed_params = []
        if new_guests != evt["guest_count"]:
            changed_params.append("guests")
        if scenario_date != evt["event_date"]:
            changed_params.append("date")
        if chosen_setting != evt["setting"].lower():
            changed_params.append("setting")

        all_task_ids_to_invalidate = set()
        if changed_params:
            task_rows = conn.execute(
                "SELECT * FROM tasks WHERE event_id = ?;", (event_id,)
            ).fetchall()
            dep_rows = conn.execute(
                """
                SELECT td.parent_task_id, td.child_task_id FROM task_dependencies td
                JOIN tasks t ON td.parent_task_id = t.id WHERE t.event_id = ?;
            """,
                (event_id,),
            ).fetchall()
            dag = build_task_dag(
                [dict(t) for t in task_rows],
                [(d["parent_task_id"], d["child_task_id"]) for d in dep_rows],
            )
            server_impacts = dag.propagate_invalidation(changed_params)
            all_task_ids_to_invalidate.update(
                imp["id"] for imp in server_impacts if imp["type"] == "TASK"
            )

        # Union with valid client-supplied task IDs strictly belonging to this event
        if invalidated_task_ids:
            for tid in invalidated_task_ids:
                row = conn.execute(
                    "SELECT id FROM tasks WHERE id = ? AND event_id = ?;", (tid, event_id)
                ).fetchone()
                if row:
                    all_task_ids_to_invalidate.add(tid)

        # Persist affected tasks as needing review (including completed tasks whose preconditions shifted)
        for tid in all_task_ids_to_invalidate:
            t_row = conn.execute(
                "SELECT status FROM tasks WHERE id = ? AND event_id = ?;", (tid, event_id)
            ).fetchone()
            prev_st = t_row["status"] if t_row else "UNKNOWN"
            conn.execute(
                """
                UPDATE tasks SET status = 'NEEDS_REVIEW', reverification_reason = ? WHERE id = ? AND event_id = ?;
            """,
                (
                    f"Invalidated by Scenario v{new_version} update ({note}) - previously {prev_st}",
                    tid,
                    event_id,
                ),
            )

        # Flag affected vendor commitments for reconfirmation if planning parameters shifted
        if changed_params:
            conn.execute(
                """
                UPDATE vendor_commitments SET needs_reconfirmation = 1 WHERE event_id = ?;
            """,
                (event_id,),
            )

        # Update event atomically checking base version
        cur = conn.execute(
            """
            UPDATE events SET guest_count = ?, setting = ?, active_scenario_version = ? 
            WHERE id = ? AND active_scenario_version = ?;
        """,
            (new_guests, chosen_setting, new_version, event_id, old_version),
        )
        if cur.rowcount == 0:
            raise ValueError(
                f"Stale proposal rejected: Base version v{old_version} was modified concurrently."
            )

        if new_date:
            conn.execute("UPDATE events SET event_date = ? WHERE id = ?;", (new_date, event_id))

        # Record audit log
        conn.execute(
            """
            INSERT INTO audit_logs (event_id, timestamp, action_type, description, previous_value, new_value)
            VALUES (?, ?, ?, ?, ?, ?);
        """,
            (
                event_id,
                now_str,
                "COMMIT_SCENARIO",
                f"Committed scenario v{new_version}: {note}",
                f"v{old_version}",
                f"v{new_version} ({new_guests} guests)",
            ),
        )

        conn.commit()
        return {"success": True, "new_version": new_version, "scenario_id": new_sc_id}


def revert_scenario_version(
    event_id: str,
    target_version: int,
    reason: str,
    db_path: str | None = None,
) -> dict[str, Any]:
    """
    Safely reverts an event by creating a new forward version from target_version items.
    Never deletes or alters payment records or historical audit logs.
    Accurately restores and snapshots event_date and setting.
    """
    target_path = db_path or get_db_path()
    now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    with get_connection(target_path) as conn:
        evt = conn.execute("SELECT * FROM events WHERE id = ?;", (event_id,)).fetchone()
        if not evt:
            raise ValueError(f"Event {event_id} not found")

        target_sc = conn.execute(
            "SELECT * FROM scenarios WHERE event_id = ? AND version = ?;",
            (event_id, target_version),
        ).fetchone()
        if not target_sc:
            raise ValueError(
                f"Target scenario version v{target_version} not found for event {event_id}"
            )

        old_version = evt["active_scenario_version"]
        new_version = old_version + 1
        new_sc_id = f"sc-{event_id}-v{new_version}"

        target_date = (
            target_sc["event_date"]
            if ("event_date" in target_sc.keys() and target_sc["event_date"])
            else evt["event_date"]
        )
        target_setting = (target_sc["setting"] or evt["setting"]).lower()

        # Fetch items from target scenario
        target_items = conn.execute(
            "SELECT * FROM budget_items WHERE scenario_id = ?;", (target_sc["id"],)
        ).fetchall()

        # Restoring planning assumptions must not undo approved contracts or revive
        # estimates that those contracts replaced. Keep their stable obligation IDs.
        current_items = conn.execute(
            """SELECT b.* FROM budget_items b JOIN scenarios s ON s.id = b.scenario_id
               WHERE s.event_id = ? AND s.status = 'ACTIVE';""",
            (event_id,),
        ).fetchall()
        restored_items = {r["obligation_id"] or r["id"]: dict(r) for r in target_items}
        for row in current_items:
            if row["approval_state"] in ("APPROVED", "REPLACED"):
                restored_items[row["obligation_id"] or row["id"]] = dict(row)

        # Archive currently active scenario
        conn.execute(
            "UPDATE scenarios SET status = 'ARCHIVED' WHERE event_id = ? AND status = 'ACTIVE';",
            (event_id,),
        )

        # Insert new active scenario representing the reverted state WITH event_date snapshotted
        conn.execute(
            """
            INSERT INTO scenarios (id, event_id, version, name, guest_count, target_budget_paise, setting, event_date, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?);
        """,
            (
                new_sc_id,
                event_id,
                new_version,
                f"Revert to v{target_version}: {reason}",
                target_sc["guest_count"],
                target_sc["target_budget_paise"],
                target_setting,
                target_date,
                now_str,
            ),
        )

        _copy_budget_items(conn, event_id, new_version, new_sc_id, list(restored_items.values()))

        _shift_task_dates(conn, event_id, evt["event_date"], target_date)
        if (target_date, target_setting, target_sc["guest_count"]) != (
            evt["event_date"],
            evt["setting"],
            evt["guest_count"],
        ):
            conn.execute(
                "UPDATE vendor_commitments SET needs_reconfirmation = 1 WHERE event_id = ?;",
                (event_id,),
            )
            conn.execute(
                """UPDATE tasks SET status = 'NEEDS_REVIEW', reverification_reason = ?
                   WHERE event_id = ?;""",
                (f"Review against restored plan v{target_version}", event_id),
            )

        conn.execute(
            """
            UPDATE events SET guest_count = ?, setting = ?, event_date = ?, active_scenario_version = ? WHERE id = ?;
        """,
            (target_sc["guest_count"], target_setting, target_date, new_version, event_id),
        )

        conn.execute(
            """
            INSERT INTO audit_logs (event_id, timestamp, action_type, description, previous_value, new_value)
            VALUES (?, ?, ?, ?, ?, ?);
        """,
            (
                event_id,
                now_str,
                "REVERT_SCENARIO",
                f"Reverted event state to match v{target_version}: {reason}",
                f"v{old_version}",
                f"v{new_version}",
            ),
        )

        conn.commit()
        return {"success": True, "new_version": new_version, "scenario_id": new_sc_id}


def record_payment(
    event_id: str,
    amount_paise: int,
    payment_method: str,
    reference_note: str,
    commitment_id: str | None = None,
    budget_item_id: str | None = None,
    idempotency_key: str | None = None,
    db_path: str | None = None,
) -> dict[str, Any]:
    """Records an actual payment transaction in the ledger, with strict idempotency and conflict protection."""
    if amount_paise <= 0:
        raise ValueError(f"Payment amount must be strictly positive, got {amount_paise}")

    target_path = db_path or get_db_path()
    now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    clean_ref = reference_note.strip()
    key = idempotency_key.strip() if idempotency_key else f"pay-op-{uuid.uuid4().hex[:16]}"

    with get_connection(target_path) as conn:
        # Cross-event tenant validation
        conn.execute("BEGIN IMMEDIATE;")
        evt = conn.execute("SELECT id FROM events WHERE id = ?;", (event_id,)).fetchone()
        if not evt:
            raise ValueError(f"Event {event_id} not found")

        # Idempotency check: if key already exists, verify payload match or raise conflict
        if idempotency_key:
            existing = conn.execute(
                "SELECT * FROM payments WHERE event_id = ? AND idempotency_key = ?;",
                (event_id, key),
            ).fetchone()
            if existing:
                same_amount = existing["amount_paise"] == amount_paise
                same_method = existing["payment_method"] == payment_method
                same_budget = (existing["budget_item_id"] or "") == (budget_item_id or "")
                same_comm = (existing["commitment_id"] or "") == (commitment_id or "")
                same_reference = existing["reference_note"] == clean_ref
                if same_amount and same_method and same_budget and same_comm and same_reference:
                    return {
                        "success": True,
                        "payment_id": existing["id"],
                        "amount_paise": existing["amount_paise"],
                        "already_recorded": True,
                        "message": "Payment already recorded with this reference (idempotent duplicate).",
                    }
                else:
                    raise ValueError(
                        f"Idempotency conflict: Key '{key}' was already used for a payment of "
                        f"₹{existing['amount_paise'] / 100:,.2f} ({existing['payment_method']}). "
                        f"Cannot reuse key for different payload."
                    )

        payment_id = f"pay-{uuid.uuid4().hex[:10]}"

        if commitment_id:
            comm = conn.execute(
                "SELECT id FROM vendor_commitments WHERE id = ? AND event_id = ?;",
                (commitment_id, event_id),
            ).fetchone()
            if not comm:
                raise ValueError(f"Commitment '{commitment_id}' not found for event '{event_id}'")

        if budget_item_id:
            b_item = conn.execute(
                """
                SELECT b.id FROM budget_items b 
                JOIN scenarios s ON b.scenario_id = s.id 
                WHERE b.id = ? AND s.event_id = ?;
            """,
                (budget_item_id, event_id),
            ).fetchone()
            if not b_item:
                raise ValueError(f"Budget item '{budget_item_id}' not found for event '{event_id}'")

        conn.execute(
            """
            INSERT INTO payments (id, event_id, commitment_id, budget_item_id, amount_paise, payment_method, reference_note, idempotency_key, paid_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
            (
                payment_id,
                event_id,
                commitment_id,
                budget_item_id,
                amount_paise,
                payment_method,
                clean_ref,
                key,
                now_str,
            ),
        )

        if commitment_id:
            conn.execute(
                """
                UPDATE vendor_commitments SET paid_amount_paise = paid_amount_paise + ? WHERE id = ? AND event_id = ?;
            """,
                (amount_paise, commitment_id, event_id),
            )

        if budget_item_id:
            conn.execute(
                """
                UPDATE budget_items SET paid_amount_paise = paid_amount_paise + ? WHERE id = ?;
            """,
                (amount_paise, budget_item_id),
            )

        conn.execute(
            """
            INSERT INTO audit_logs (event_id, timestamp, action_type, description, previous_value, new_value)
            VALUES (?, ?, ?, ?, ?, ?);
        """,
            (
                event_id,
                now_str,
                "RECORD_PAYMENT",
                f"Recorded payment of ₹{amount_paise / 100:,.2f} via {payment_method} ({reference_note})",
                None,
                f"Payment {payment_id}",
            ),
        )

        conn.commit()
        return {
            "success": True,
            "payment_id": payment_id,
            "amount_paise": amount_paise,
            "already_recorded": False,
        }


def approve_vendor_quote_in_db(
    event_id: str,
    vendor_name: str,
    category: str,
    items: list[dict[str, Any]],
    advance_deposit_paise: int = 0,
    deposit_due_date: str | None = None,
    notes: str | None = None,
    supersedes_item_id: str | None = None,
    supersedes_item_ids: list[str] | None = None,
    idempotency_key: str | None = None,
    db_path: str | None = None,
) -> dict[str, Any]:
    """
    Approves a vendor quote into the active scenario ledger in one atomic transaction.
    1. Recomputes exact line items and tiered math with taxes.
    2. Enforces idempotency against retried approvals.
    3. Prevents double-counting by superseding matching estimated items.
    4. Records deposit obligation strictly on commitment level to prevent multiplication.
    """
    target_path = db_path or get_db_path()
    now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    with get_connection(target_path) as conn:
        conn.execute("BEGIN IMMEDIATE;")
        data = get_event_by_id(event_id, target_path)
        if not data:
            raise ValueError(f"Event {event_id} not found")

        fingerprint = json.dumps(
            [
                vendor_name,
                category,
                items,
                advance_deposit_paise,
                deposit_due_date,
                notes,
                supersedes_item_id,
                supersedes_item_ids,
            ],
            sort_keys=True,
        )
        # Idempotency check
        if idempotency_key:
            existing = conn.execute(
                "SELECT * FROM vendor_commitments WHERE event_id = ? AND idempotency_key = ?;",
                (event_id, idempotency_key),
            ).fetchone()
            if existing:
                if existing["request_fingerprint"] != fingerprint:
                    raise ValueError(
                        "Idempotency conflict: approval key belongs to a different or older quote."
                    )
                return {
                    "success": True,
                    "commitment_id": existing["id"],
                    "already_approved": True,
                    "message": "Quote already approved with this key.",
                }

        scenario_id = data["active_scenario"]["id"]
        guests = data["event"]["guest_count"]
        total_quote_paise = 0
        new_item_ids = []
        if not items:
            raise ValueError("A quote must contain at least one confirmed line item.")

        # Validate that unconfirmed zero prices cannot be approved without price input
        for it in items:
            unit = max(0, int(it.get("unit_cost_paise", 0)))
            notes_str = str(it.get("notes") or "")
            if unit == 0 and (
                "PRICE_UNCONFIRMED" in notes_str or "unconfirmed" in notes_str.lower()
            ):
                raise ValueError(
                    "Cannot approve quote with unconfirmed zero price. Please provide confirmed rate before committing."
                )

        # Mark superseded estimated items to eliminate double-counting with strict tenant isolation
        if supersedes_item_ids is not None:
            for s_id in supersedes_item_ids:
                row = conn.execute(
                    "SELECT id FROM budget_items WHERE id = ? AND scenario_id = ?;",
                    (s_id, scenario_id),
                ).fetchone()
                if not row:
                    raise ValueError(
                        f"Cross-event violation: Item '{s_id}' does not belong to active scenario of event '{event_id}'"
                    )
                conn.execute(
                    "UPDATE budget_items SET approval_state = 'REPLACED' WHERE id = ? AND scenario_id = ?;",
                    (s_id, scenario_id),
                )
        elif supersedes_item_id:
            row = conn.execute(
                "SELECT id FROM budget_items WHERE id = ? AND scenario_id = ?;",
                (supersedes_item_id, scenario_id),
            ).fetchone()
            if not row:
                raise ValueError(
                    f"Cross-event violation: Item '{supersedes_item_id}' does not belong to active scenario of event '{event_id}'"
                )
            conn.execute(
                "UPDATE budget_items SET approval_state = 'REPLACED' WHERE id = ? AND scenario_id = ?;",
                (supersedes_item_id, scenario_id),
            )
        else:
            # Auto-supersede estimated items in the same category within THIS scenario
            conn.execute(
                """
                UPDATE budget_items SET approval_state = 'REPLACED'
                WHERE scenario_id = ? AND category = ? AND approval_state = 'ESTIMATED';
            """,
                (scenario_id, category),
            )

        for it in items:
            unit = max(0, int(it.get("unit_cost_paise", 0)))
            model = it.get("pricing_model", "FIXED")
            cap = max(1, int(it.get("step_capacity", 1)))
            tax_rate = max(0, min(10000, int(it.get("tax_rate_bps", 0))))

            calc = compute_line_item_paise(
                model, unit, guests, cap, tax_rate, bool(it.get("is_tax_inclusive", False))
            )
            total_quote_paise += calc["total_paise"]

            item_id = f"item-quote-{uuid.uuid4().hex[:10]}"
            new_item_ids.append(item_id)
            # Item deposit obligation is 0 to avoid multiplication across multi-item quotes;
            # the authoritative deposit obligation is held on the vendor_commitments record.
            conn.execute(
                """
                INSERT INTO budget_items (id, scenario_id, category, name, pricing_model, unit_cost_paise, step_capacity, tax_rate_bps, approval_state, deposit_required_paise, paid_amount_paise, deposit_due_date, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'APPROVED', 0, 0, ?, ?);
            """,
                (
                    item_id,
                    scenario_id,
                    category,
                    it["name"],
                    model,
                    unit,
                    cap,
                    tax_rate,
                    deposit_due_date,
                    notes,
                ),
            )
            conn.execute(
                "UPDATE budget_items SET is_tax_inclusive = ? WHERE id = ?;",
                (int(bool(it.get("is_tax_inclusive", False))), item_id),
            )

        com_id = f"com-{uuid.uuid4().hex[:10]}"
        if advance_deposit_paise > total_quote_paise:
            raise ValueError("Advance cannot exceed the total quote. Review the extracted amount.")
        conn.execute(
            """
            INSERT INTO vendor_commitments (id, event_id, category, vendor_name, approval_state, total_quote_paise, deposit_required_paise, paid_amount_paise, deposit_due_date, hidden_fee_question, negotiation_script, raw_quote_text, is_reviewed, needs_reconfirmation, idempotency_key)
            VALUES (?, ?, ?, ?, 'APPROVED', ?, ?, 0, ?, ?, ?, ?, 1, 0, ?);
        """,
            (
                com_id,
                event_id,
                category,
                vendor_name,
                total_quote_paise,
                advance_deposit_paise,
                deposit_due_date,
                "Are kitchen fuel cylinders and generator diesel included?",
                f"Hi {vendor_name}, quote approved.",
                notes or "Extracted & approved via Planqira",
                idempotency_key,
            ),
        )
        conn.execute(
            "UPDATE vendor_commitments SET request_fingerprint = ? WHERE id = ?;",
            (fingerprint, com_id),
        )

        conn.execute(
            """
            INSERT INTO audit_logs (event_id, timestamp, action_type, description, previous_value, new_value)
            VALUES (?, ?, ?, ?, ?, ?);
        """,
            (
                event_id,
                now_str,
                "APPROVE_VENDOR_QUOTE",
                f"Approved quote from {vendor_name} ({category}) with deposit requirement of ₹{advance_deposit_paise / 100:,.2f}",
                "QUOTED",
                f"APPROVED (₹{total_quote_paise / 100:,.2f})",
            ),
        )

        conn.commit()
        return {
            "success": True,
            "commitment_id": com_id,
            "total_quote_paise": total_quote_paise,
            "item_ids": new_item_ids,
            "message": f"Approved quote from {vendor_name} and recorded in ledger without premature payment mark.",
        }


def create_incident(
    event_id: str,
    severity: str,
    title: str,
    description: str,
    resolution: str | None = None,
    db_path: str | None = None,
) -> dict[str, Any]:
    """Records an operational event-day incident with resolution tracking."""
    target_path = db_path or get_db_path()
    now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    inc_id = f"inc-{uuid.uuid4().hex[:10]}"

    with get_connection(target_path) as conn:
        conn.execute(
            """
            INSERT INTO incidents (id, event_id, severity, title, description, resolution, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
            (
                inc_id,
                event_id,
                severity,
                title,
                description,
                resolution,
                "RESOLVED" if resolution else "OPEN",
                now_str,
            ),
        )

        conn.execute(
            """
            INSERT INTO audit_logs (event_id, timestamp, action_type, description, previous_value, new_value)
            VALUES (?, ?, ?, ?, ?, ?);
        """,
            (
                event_id,
                now_str,
                "LOG_INCIDENT",
                f"Logged {severity} incident: {title}",
                None,
                inc_id,
            ),
        )

        conn.commit()
        return {"success": True, "incident_id": inc_id}


def list_incidents(event_id: str, db_path: str | None = None) -> list[dict[str, Any]]:
    target_path = db_path or get_db_path()
    with get_connection(target_path) as conn:
        rows = conn.execute(
            "SELECT * FROM incidents WHERE event_id = ? ORDER BY created_at DESC;", (event_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def update_task_status(
    task_id: str, status: str, event_id: str | None = None, db_path: str | None = None
) -> bool:
    target_path = db_path or get_db_path()
    with get_connection(target_path) as conn:
        if event_id:
            cur = conn.execute(
                "UPDATE tasks SET status = ? WHERE id = ? AND event_id = ?;",
                (status, task_id, event_id),
            )
        else:
            cur = conn.execute("UPDATE tasks SET status = ? WHERE id = ?;", (status, task_id))
        conn.commit()
        return cur.rowcount > 0


def update_runbook_status(
    cue_id: str, status: str, event_id: str | None = None, db_path: str | None = None
) -> bool:
    target_path = db_path or get_db_path()
    with get_connection(target_path) as conn:
        if event_id:
            cur = conn.execute(
                "UPDATE runbook_cues SET status = ? WHERE id = ? AND event_id = ?;",
                (status, cue_id, event_id),
            )
        else:
            cur = conn.execute("UPDATE runbook_cues SET status = ? WHERE id = ?;", (status, cue_id))
        conn.commit()
        return cur.rowcount > 0
