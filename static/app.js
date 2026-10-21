/**
 * Planqira — Client-Side Application Controller
 * Safe DOM rendering (zero unsafe innerHTML text interpolation),
 * state synchronization, and deterministic API client.
 */

let currentEventId = "";
let currentEventData = null;
let latestSimResult = null;
let parsedQuoteData = null;

const sampleQuotes = {
  1: "Namaste! This is Udaipur Royal Feast Caterers. For your Royal Wedding, our Signature Dal Baati Churma & Multi-Cuisine Dinner Buffet is Rs 2200 per guest + 5% GST. Minimum advance token is Rs 150000 to lock date by 25th Oct. Note: Kitchen diesel and generator cylinder fuel charged extra Rs 15000.",
  2: "Hi, this is DJ Aman Sound & Light. Truss lighting, JBL line array setup and smoke machines for Sangeet night is Rs 140000 flat + 18% GST. Advance Rs 40000 due within 7 days. Overtime past 11:30 PM is Rs 18000 per hour.",
  3: "Mandapam Decorators: Complete floral mandap with fresh Rajnigandha, brass urlis, entrance archway and stage sofa is Rs 320000 flat + 18% GST. Advance Rs 80000 needed. Note: Transport beyond city limits charged Rs 80 per km."
};

// Safe DOM Creation Helper
function el(tag, attrs = {}, children = []) {
  const element = document.createElement(tag);
  for (const [key, val] of Object.entries(attrs)) {
    if (key === "className") {
      element.className = val;
    } else if (key === "style" && typeof val === "object") {
      Object.assign(element.style, val);
    } else if (key.startsWith("on") && typeof val === "function") {
      element.addEventListener(key.slice(2).toLowerCase(), val);
    } else {
      element.setAttribute(key, val);
    }
  }
  for (const child of Array.isArray(children) ? children : [children]) {
    if (child === null || child === undefined) continue;
    if (typeof child === "string" || typeof child === "number") {
      element.appendChild(document.createTextNode(String(child)));
    } else if (child instanceof Node) {
      element.appendChild(child);
    }
  }
  return element;
}

function formatPaise(paise) {
  if (paise === undefined || paise === null) return "₹0.00";
  const rs = paise / 100;
  return "₹" + rs.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// 1. Health & Startup
async function checkHealth() {
  try {
    const res = await requestAPI("/api/health");
    if (!res.ok) throw new Error("Assistant status unavailable");
    const data = await res.json();
    const pill = document.getElementById("connectionPill");
    pill.textContent = "";
    
    if (data.has_server_key) {
      pill.className = "status-badge badge-green";
      pill.appendChild(document.createTextNode("Quote assistant: AI configured"));
    } else {
      pill.className = "status-badge badge-amber";
      pill.appendChild(document.createTextNode("Quote assistant: basic mode"));
    }
  } catch (e) {
    document.getElementById("connectionPill").textContent = "Quote assistant: status unavailable";
  }
}

// 2. Events Loading
async function loadEvents() {
  setWorkspaceLoading(true);
  try {
    const res = await requestAPI("/api/events");
    if (!res.ok) throw new Error("Events could not be loaded. Please try again.");
    const data = await res.json();
    const picker = document.getElementById("eventSelector");
    if (!picker) return;
    picker.innerHTML = "";

    data.events.forEach(ev => {
      const opt = document.createElement("option");
      opt.value = ev.id;
      opt.textContent = `${ev.title} (${ev.city}) — ${ev.guest_count} Guests`;
      picker.appendChild(opt);
    });

    const urlParams = new URLSearchParams(window.location.search);
    const requestedEvent = urlParams.get("event");
    const requestedTab = urlParams.get("tab");
    const requestedGuests = urlParams.get("guests");

    if (requestedEvent && data.events.some(e => e.id === requestedEvent)) {
      currentEventId = requestedEvent;
      picker.value = requestedEvent;
    } else if (data.events.length > 0) {
      currentEventId = data.events[0].id;
      picker.value = currentEventId;
    }

    if (currentEventId) {
      await loadEventDetails(currentEventId);
    } else {
      currentEventData = null;
      document.body.classList.add("is-empty");
      document.getElementById("emptyState").hidden = false;
      setWorkspaceLoading(false);
      document.getElementById("syncStatus").textContent = "Ready to create an event";
    }

    if (requestedTab) {
      switchTab(requestedTab);
    }

    if (requestedGuests && currentEventData) {
      const slider = document.getElementById("simHeadcountSlider");
      if (slider) {
        slider.value = requestedGuests;
        onHeadcountSliderChange(requestedGuests);
        if (requestedTab === "tabScenario") {
          runScenarioSimulation();
        }
      }
    }
  } catch (e) {
    showLoadError(e.message);
  }
}

let eventRequestSequence = 0;
async function switchEvent(eventId) {
  latestSimResult = null;
  parsedQuoteData = null;
  currentEventId = eventId;
  const url = new URL(location.href);
  url.searchParams.set("event", eventId);
  url.searchParams.delete("guests");
  history.replaceState(null, "", url);
  await loadEventDetails(eventId);
}

async function loadEventDetails(eventId) {
  const request = ++eventRequestSequence;
  setWorkspaceLoading(true, Boolean(currentEventData));
  try {
    const res = await requestAPI(`/api/events/${encodeURIComponent(eventId)}`);
    if (!res.ok) throw new Error("This event could not be loaded. Refresh to try again.");
    const data = await res.json();
    if (request !== eventRequestSequence) return;
    currentEventData = data;
    currentEventId = eventId;
    latestSimResult = null;
    renderAll(data);
    renderOverview(data);
    document.getElementById("syncStatus").textContent = `Updated ${new Date().toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'})}`;
  } catch (e) {
    if (request === eventRequestSequence) showLoadError(e.message);
  } finally {
    if (request === eventRequestSequence) setWorkspaceLoading(false);
  }
}

// 3. Render Entire UI
function renderAll(data) {
  const evt = data.event;
  const sol = data.solvency;

  // Event Header
  document.getElementById("headerEventTitle").textContent = evt.title;
  document.getElementById("metaTypeCity").textContent = `${evt.event_type.toUpperCase()} • ${evt.city} (${evt.setting.toUpperCase()})`;
  document.getElementById("metaDateTime").textContent = `${evt.event_date} at ${evt.start_time || '15:00'} (${evt.duration_hours || 5} hrs, ${evt.timezone})`;
  document.getElementById("metaGuests").textContent = `${evt.guest_count} Guests`;
  document.getElementById("metaVersionBadge").textContent = `Scenario v${evt.active_scenario_version}`;

  // Financial Aligned Summary Strip
  document.getElementById("finBudget").textContent = formatPaise(sol.target_budget_paise);
  document.getElementById("finReserve").textContent = formatPaise(sol.contingency_paise);
  document.getElementById("finProjected").textContent = formatPaise(sol.total_projected_paise);
  document.getElementById("finCommitted").textContent = formatPaise(sol.total_approved_commitments_paise || 0);
  document.getElementById("finPaid").textContent = formatPaise(sol.total_paid_paise);
  document.getElementById("finOutstanding").textContent = formatPaise(sol.total_outstanding_paise || 0);

  const finVar = document.getElementById("finVariance");
  const finSolv = document.getElementById("finSolvencyStatus");
  const defBanner = document.getElementById("deficitBanner");

  if (sol.solvency_status === "SOLVENT") {
    finVar.textContent = `+${formatPaise(sol.variance_paise)}`;
    finVar.style.color = "var(--status-green)";
    finSolv.textContent = "Within budget";
    finSolv.className = "status-badge badge-green";
    defBanner.style.display = "none";
  } else {
    finVar.textContent = `-${formatPaise(Math.abs(sol.variance_paise))}`;
    finVar.style.color = "var(--status-red)";
    finSolv.textContent = "Over budget";
    finSolv.className = "status-badge badge-red";
    defBanner.style.display = "block";
  }

  // 02. Ideas Workspace
  renderIdeas(data.themes || []);

  // 03. Budget & Commitments Workspace
  renderBudgetTable(sol.items || []);
  renderVendorsTable(data.vendors || []);
  renderPaymentsTable(data.payments || []);

  // 04. Timeline & Tasks Workspace
  renderTasksTable(data.tasks || []);

  // 05. Event Day Operations Workspace
  renderRunbookTable(data.runbook || []);
  renderIncidentsTable(data.incidents || []);

  // 06. Scenario Lab Workspace
  initScenarioLab(evt);

  // Audit Log in Mission summary
  renderAuditLogs(data.audit_logs || []);
}

// 01. Ideas Render
function renderIdeas(themes) {
  const container = document.getElementById("themesContainer");
  container.innerHTML = "";

  themes.forEach(th => {
    const swatches = el("div", { className: "swatches" }, 
      (th.palette_hex || []).map(hex => el("div", { className: "swatch-item", style: { background: hex }, title: hex }))
    );

    const card = el("div", { className: `concept-panel ${th.is_selected ? 'selected' : ''}` }, [
      el("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "baseline" } }, [
        el("div", { style: { fontWeight: "700", fontSize: "1.05rem" } }, th.name),
        th.is_selected ? el("span", { className: "status-badge badge-green" }, "Active Concept") : null
      ]),
      el("div", { style: { fontSize: "0.82rem", color: "var(--text-secondary)" } }, th.tagline),
      swatches,
      el("div", { style: { fontSize: "0.8rem" } }, [
        el("strong", {}, "Sensory Hook: "),
        document.createTextNode(th.sensory_hook)
      ]),
      el("div", { style: { fontSize: "0.8rem" } }, [
        el("strong", {}, "Signature Moment: "),
        document.createTextNode(th.signature_moment)
      ]),
      el("div", { style: { fontSize: "0.78rem", background: "var(--surface-subtle)", padding: "0.5rem", borderRadius: "4px", borderLeft: "3px solid var(--accent)" } }, [
        el("strong", {}, "Affordable DIY Alternative: "),
        document.createTextNode(th.diy_swap)
      ])
    ]);

    container.appendChild(card);
  });
}

// 02. Budget & Commitments Render
function renderBudgetTable(items) {
  const tbody = document.getElementById("budgetTableBody");
  tbody.innerHTML = "";

  items.forEach(it => {
    const tr = el("tr", {}, [
      el("td", {}, it.category),
      el("td", { style: { fontWeight: "600" } }, it.name),
      el("td", {}, el("span", { className: "status-badge badge-neutral" }, it.pricing_model)),
      el("td", { className: "numeric" }, formatPaise(it.unit_cost_paise)),
      el("td", { className: "numeric" }, it.quantity),
      el("td", { className: "numeric" }, formatPaise(it.subtotal_paise)),
      el("td", { className: "numeric" }, `${it.tax_rate_bps / 100}%`),
      el("td", { className: "numeric" }, formatPaise(it.tax_paise)),
      el("td", { className: "numeric", style: { fontWeight: "700" } }, formatPaise(it.total_paise)),
      el("td", {}, el("span", { className: `status-badge ${it.approval_state === 'APPROVED' ? 'badge-green' : (it.approval_state === 'QUOTED' ? 'badge-amber' : 'badge-neutral')}` }, it.approval_state)),
      el("td", {}, el("span", { className: `status-badge ${it.calculated_payment_status === 'PAID' ? 'badge-green' : (it.calculated_payment_status === 'PARTIAL' ? 'badge-amber' : 'badge-neutral')}` }, it.calculated_payment_status)),
      el("td", { className: "numeric" }, formatPaise(it.paid_amount_paise))
    ]);
    tbody.appendChild(tr);
  });
}

function renderVendorsTable(vendors) {
  const tbody = document.getElementById("vendorTableBody");
  tbody.innerHTML = "";

  vendors.forEach(v => {
    const waText = encodeURIComponent(`Hi ${v.vendor_name}, following up regarding event "${currentEventData.event.title}". Total quote: ₹${v.total_quote_paise/100}.`);
    const waLink = el("a", {
      href: `https://wa.me/?text=${waText}`,
      target: "_blank",
      className: "btn btn-sm",
      style: { color: "var(--status-green)", borderColor: "var(--status-green-border)" }
    }, "💬 WhatsApp");

    const reconfirmBadge = v.needs_reconfirmation ? el("span", { className: "status-badge badge-red", style: { marginLeft: "0.4rem" } }, "Reconfirm Needed") : null;

    const tr = el("tr", {}, [
      el("td", {}, v.category),
      el("td", { style: { fontWeight: "600" } }, [document.createTextNode(v.vendor_name), reconfirmBadge]),
      el("td", {}, el("span", { className: `status-badge ${v.approval_state === 'APPROVED' ? 'badge-green' : 'badge-amber'}` }, v.approval_state)),
      el("td", { className: "numeric", style: { fontWeight: "700" } }, formatPaise(v.total_quote_paise)),
      el("td", { className: "numeric" }, formatPaise(v.deposit_required_paise || 0)),
      el("td", { className: "numeric" }, formatPaise(v.paid_amount_paise || 0)),
      el("td", {}, waLink),
      el("td", { style: { fontSize: "0.8rem", color: "var(--text-secondary)" } }, v.hidden_fee_question || "—")
    ]);
    tbody.appendChild(tr);
  });
}

function renderPaymentsTable(payments) {
  const tbody = document.getElementById("paymentsTableBody");
  tbody.innerHTML = "";

  if (!payments || payments.length === 0) {
    tbody.appendChild(el("tr", {}, el("td", { colSpan: 5, style: { textAlign: "center", color: "var(--text-muted)" } }, "No cash payments recorded yet.")));
    return;
  }

  payments.forEach(p => {
    const tr = el("tr", {}, [
      el("td", { style: { fontFamily: "var(--font-mono)", fontSize: "0.75rem" } }, p.paid_at.replace("T", " ").replace("Z", "")),
      el("td", { className: "numeric", style: { fontWeight: "700", color: "var(--status-green)" } }, formatPaise(p.amount_paise)),
      el("td", {}, el("span", { className: "status-badge badge-neutral" }, p.payment_method)),
      el("td", {}, p.reference_note),
      el("td", { style: { fontSize: "0.75rem", color: "var(--text-muted)" } }, p.id)
    ]);
    tbody.appendChild(tr);
  });
}

// 03. Timeline & Operations Render
function renderTasksTable(tasks) {
  const tbody = document.getElementById("tasksTableBody");
  tbody.innerHTML = "";

  tasks.forEach(t => {
    const isDone = t.status === "DONE";
    const isReview = t.status === "NEEDS_REVIEW";
    const statusBtn = el("button", {
      className: `btn btn-sm ${isDone ? 'btn-primary' : ''}`,
      onclick: () => toggleTaskStatus(t.id, isDone ? "PENDING" : "DONE")
    }, isDone ? "✓ Done" : "Mark Done");

    const sensitiveBadge = t.depends_on_guests ? el("span", { className: "status-badge badge-amber", style: { fontSize: "0.68rem", marginLeft: "0.3rem" } }, "Headcount Sensitive") : null;
    const reviewCallout = isReview ? el("div", { style: { fontSize: "0.75rem", color: "var(--status-red)", marginTop: "0.2rem" } }, `⚠️ ${t.reverification_reason || 'Requires reverification'}`) : null;

    const tr = el("tr", {}, [
      el("td", { style: { fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: "600" } }, t.timeframe),
      el("td", {}, [
        el("span", { style: { textDecoration: isDone ? 'line-through' : 'none' } }, t.title),
        sensitiveBadge,
        reviewCallout
      ]),
      el("td", {}, t.owner),
      el("td", {}, t.due_date),
      el("td", {}, el("span", { className: `status-badge ${t.priority === 'CRITICAL' ? 'badge-red' : 'badge-neutral'}` }, t.priority)),
      el("td", {}, statusBtn)
    ]);
    tbody.appendChild(tr);
  });
}

function renderRunbookTable(cues) {
  const tbody = document.getElementById("runbookTableBody");
  tbody.innerHTML = "";

  cues.forEach(c => {
    const tr = el("tr", {}, [
      el("td", { style: { fontFamily: "var(--font-mono)", fontWeight: "700", color: "var(--accent)" } }, c.time_slot),
      el("td", { style: { fontWeight: "500" } }, c.front_of_house),
      el("td", { style: { color: "var(--text-secondary)" } }, c.back_of_house),
      el("td", {}, el("span", { className: "status-badge badge-neutral" }, c.lead_role)),
      el("td", {}, el("button", {
        className: "btn btn-sm",
        onclick: () => toggleRunbookStatus(c.id, c.status === "COMPLETED" ? "PENDING" : "COMPLETED")
      }, c.status === "COMPLETED" ? "Completed" : "Active"))
    ]);
    tbody.appendChild(tr);
  });
}

function renderIncidentsTable(incidents) {
  const tbody = document.getElementById("incidentsTableBody");
  tbody.innerHTML = "";

  if (!incidents || incidents.length === 0) {
    tbody.appendChild(el("tr", {}, el("td", { colSpan: 5, style: { textAlign: "center", color: "var(--text-muted)" } }, "No incidents logged. Operations running normally.")));
    return;
  }

  incidents.forEach(inc => {
    const sevBadge = inc.severity === "CRITICAL" ? "badge-red" : (inc.severity === "HIGH" ? "badge-amber" : "badge-neutral");
    const tr = el("tr", {}, [
      el("td", { style: { fontFamily: "var(--font-mono)", fontSize: "0.75rem" } }, inc.created_at.replace("T", " ").replace("Z", "")),
      el("td", {}, el("span", { className: `status-badge ${sevBadge}` }, inc.severity)),
      el("td", { style: { fontWeight: "600" } }, inc.title),
      el("td", {}, inc.description),
      el("td", { style: { color: inc.resolution ? "var(--status-green)" : "var(--text-muted)" } }, inc.resolution || "Under Investigation")
    ]);
    tbody.appendChild(tr);
  });
}

function renderAuditLogs(logs) {
  const tbody = document.getElementById("auditLogTableBody");
  tbody.innerHTML = "";

  logs.forEach(l => {
    const tr = el("tr", {}, [
      el("td", { style: { fontFamily: "var(--font-mono)", fontSize: "0.75rem" } }, l.timestamp.replace("T", " ").replace("Z", "")),
      el("td", {}, el("span", { className: "status-badge badge-neutral" }, l.action_type)),
      el("td", {}, l.description),
      el("td", { style: { color: "var(--text-muted)" } }, l.previous_value || "—"),
      el("td", { style: { color: "var(--status-green)", fontWeight: "500" } }, l.new_value || "—")
    ]);
    tbody.appendChild(tr);
  });
}

// 04. Scenario Lab
function initScenarioLab(evt) {
  document.getElementById("simHeadcountSlider").value = evt.guest_count;
  document.getElementById("simHeadcountVal").textContent = evt.guest_count;
  document.getElementById("simSettingSelect").value = evt.setting;
  document.getElementById("simDateInput").value = evt.event_date;

  document.getElementById("simSummarySection").style.display = "none";
  document.getElementById("simDiffCard").style.display = "none";
  document.getElementById("simDagCallout").style.display = "none";
}

function onHeadcountSliderChange(val) {
  invalidatePreview();
  document.getElementById("simHeadcountVal").textContent = val;
}

async function runScenarioSimulation() {
  const eventId = currentEventId;
  const baseVersion = currentEventData.event.active_scenario_version;
  const previewSequence = ++simulationSequence;
  const guests = parseInt(document.getElementById("simHeadcountSlider").value, 10);
  const setting = document.getElementById("simSettingSelect").value;
  const date = document.getElementById("simDateInput").value;

  try {
    const res = await requestAPI(`/api/events/${currentEventId}/simulate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        new_guests: guests,
        new_setting: setting,
        new_date: date,
        base_version: currentEventData.event.active_scenario_version
      })
    });
    const sim = await res.json();
    if (eventId !== currentEventId || previewSequence !== simulationSequence) return;
    latestSimResult = {...sim, previewBaseVersion: baseVersion};

    document.getElementById("simSummarySection").style.display = "flex";
    document.getElementById("simDiffCard").style.display = "block";

    // Delta Display
    const deltaEl = document.getElementById("simSpendDelta");
    if (sim.cost_delta_paise >= 0) {
      deltaEl.textContent = `+${formatPaise(sim.cost_delta_paise)}`;
      deltaEl.style.color = "var(--status-red)";
    } else {
      deltaEl.textContent = `${formatPaise(sim.cost_delta_paise)}`;
      deltaEl.style.color = "var(--status-green)";
    }

    const solEl = document.getElementById("simSolvencyBadge");
    solEl.textContent = sim.simulated_solvency_status;
    solEl.className = `status-badge ${sim.simulated_solvency_status === 'SOLVENT' ? 'badge-green' : 'badge-red'}`;

    document.getElementById("simTradeoffsText").textContent = (sim.tradeoffs || []).join(" ") || "No financial trade-offs triggered.";

    // DAG Impacts
    const dagBox = document.getElementById("simDagCallout");
    const dagList = document.getElementById("simDagList");
    dagList.innerHTML = "";

    if (sim.dag_impacts && sim.dag_impacts.length > 0) {
      dagBox.style.display = "block";
      sim.dag_impacts.forEach(impact => {
        const item = el("div", { style: { marginBottom: "0.3rem" } }, [
          el("strong", {}, impact.title),
          document.createTextNode(` — ${impact.reason} (${impact.new_action})`)
        ]);
        dagList.appendChild(item);
      });
    } else {
      dagBox.style.display = "none";
    }

    // Diff Table
    const diffTbody = document.getElementById("simDiffTableBody");
    diffTbody.innerHTML = "";

    sim.item_diffs.forEach(d => {
      const deltaColor = d.delta_paise > 0 ? "var(--status-red)" : (d.delta_paise < 0 ? "var(--status-green)" : "var(--text-muted)");
      const tr = el("tr", {}, [
        el("td", { style: { fontWeight: "600" } }, d.name),
        el("td", {}, el("span", { className: "status-badge badge-neutral" }, d.pricing_model)),
        el("td", { className: "numeric" }, d.base_quantity),
        el("td", { className: "numeric", style: { fontWeight: "700" } }, d.new_quantity),
        el("td", { className: "numeric" }, formatPaise(d.unit_cost_paise)),
        el("td", { className: "numeric" }, formatPaise(d.base_total_paise)),
        el("td", { className: "numeric", style: { fontWeight: "700" } }, formatPaise(d.new_total_paise)),
        el("td", { className: "numeric", style: { color: deltaColor, fontWeight: "700" } }, `${d.delta_paise >= 0 ? '+' : ''}${formatPaise(d.delta_paise)}`)
      ]);
      diffTbody.appendChild(tr);
    });

  } catch (e) {
    console.error("Simulation error:", e);
  }
}

async function commitScenarioAction() {
  if (!latestSimResult) return;

  const guests = latestSimResult.new_guests;
  const setting = latestSimResult.new_setting;
  const date = latestSimResult.new_date;
  const baseVersion = latestSimResult.previewBaseVersion;
  const invalidatedTaskIds = (latestSimResult.dag_impacts || []).map(i => i.id);

  const payload = {
    new_guests: guests,
    new_setting: setting,
    new_date: date,
    base_version: baseVersion,
    note: `Headcount shift to ${guests} (${setting})`,
    new_budget_items: currentEventData.budget_items.map(it => ({
      id: it.id,
      category: it.category,
      name: it.name,
      pricing_model: it.pricing_model,
      unit_cost_paise: it.unit_cost_paise,
      step_capacity: it.step_capacity,
      tax_rate_bps: it.tax_rate_bps,
      approval_state: it.approval_state,
      deposit_required_paise: it.deposit_required_paise || 0,
      paid_amount_paise: it.paid_amount_paise || 0,
      deposit_due_date: it.deposit_due_date,
      notes: it.notes
    })),
    invalidated_task_ids: invalidatedTaskIds
  };

  try {
    const res = await requestAPI(`/api/events/${currentEventId}/commit-scenario`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.status === 409) {
      showNotice("Proposal rejected: event has been updated to a newer version by another edit. Please re-run simulation.");
      await loadEventDetails(currentEventId);
      return;
    }
    const result = await res.json();
    if (result.success) {
      showNotice(`Committed Scenario v${result.new_version}! Affected tasks flagged for review.`);
      await loadEventDetails(currentEventId);
      switchTab("tabBudget");
    }
  } catch (e) {
    console.error("Error committing scenario:", e);
    showNotice("Failed to commit scenario.");
  }
}

// 5. Tab Switching (6 Workspaces with Persistent Sidebar)
const workspaceInfo = {
  tabOverview: ["Overview", "A clear view of your celebration.", "Your budget, next steps, and recent decisions in one place.", "Review a vendor quote", () => openQuoteModal()],
  tabIdeas: ["Ideas & inspiration", "Give your celebration a direction.", "Explore themes and practical details that make the day your own.", "View the checklist", () => switchTab('tabTimeline')],
  tabBudget: ["Budget & vendors", "Know where your budget goes.", "Review estimated costs, agreed quotes, and payments separately.", "Review a vendor quote", () => openQuoteModal()],
  tabTimeline: ["Planning checklist", "One step closer to the day.", "Work through the preparation tasks. Recheck anything affected by a plan change.", "View event day", () => switchTab('tabEventDay')],
  tabEventDay: ["Event-day schedule", "Keep the day running smoothly.", "Follow the schedule, use a backup plan, and record any issues.", "Report an issue", () => openIncidentModal()],
  tabScenario: ["Explore changes", "What if your plans change?", "Preview costs and affected tasks. Your saved plan stays unchanged until you commit.", "How it works", () => showDemoGuide()]
};
function switchTab(tabId) {
  if (!workspaceInfo[tabId]) tabId = 'tabOverview';
  const info = workspaceInfo[tabId];
  document.querySelectorAll('.workspace-pane').forEach(p => p.classList.toggle('active', p.id === tabId));
  const ids = ['navBtnOverview', 'navBtnIdeas', 'navBtnBudget', 'navBtnTimeline', 'navBtnEventDay', 'navBtnScenario'];
  Object.keys(workspaceInfo).forEach((key, i) => {
    const button = document.getElementById(ids[i]);
    button.classList.toggle('active', key === tabId);
    if (key === tabId) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
  });
  document.body.dataset.workspace = tabId;
  document.getElementById('pageTitle').textContent = info[0];
  document.getElementById('workspaceTitle').textContent = info[1];
  document.getElementById('workspaceDescription').textContent = info[2];
  const action = document.getElementById('workspaceAction');
  action.textContent = info[3]; action.onclick = info[4];
  const url = new URL(location.href); url.searchParams.set('tab', tabId);
  history.replaceState(null, '', url);
  if (matchMedia('(max-width: 760px)').matches) toggleSidebar(false);
}

// 6. Task & Runbook Status Actions
async function toggleTaskStatus(taskId, newStatus) {
  try {
    const res = await requestAPI(`/api/events/${currentEventId}/tasks/${taskId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus })
    });
    if (res.ok) await loadEventDetails(currentEventId);
  } catch (e) {
    console.error("Error updating task:", e);
  }
}

async function toggleRunbookStatus(cueId, newStatus) {
  try {
    const res = await requestAPI(`/api/events/${currentEventId}/runbook/${cueId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus })
    });
    if (res.ok) await loadEventDetails(currentEventId);
  } catch (e) {
    console.error("Error updating runbook cue:", e);
  }
}

// 7. Accessible Modals (Focus Trap, Escape Dismiss, Backdrop Click)
let lastFocusedElement = null;

function openModal(id) {
  if (matchMedia('(max-width: 760px)').matches) toggleSidebar(false);
  lastFocusedElement = document.activeElement;
  const modal = document.getElementById(id);
  if (modal) {
    modal.classList.add("open");
    const focusable = modal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    if (focusable.length > 0) focusable[0].focus();
  }
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.classList.remove("open");
  }
  if (lastFocusedElement) {
    lastFocusedElement.focus();
  }
}

// Global modal accessibility listeners
window.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    document.querySelectorAll(".modal-overlay.open").forEach(modal => {
      modal.classList.remove("open");
    });
    if (lastFocusedElement) lastFocusedElement.focus();
  }
});

document.addEventListener("click", (e) => {
  if (e.target && e.target.classList && e.target.classList.contains("modal-overlay")) {
    e.target.classList.remove("open");
    if (lastFocusedElement) lastFocusedElement.focus();
  }
});

// Create Event Modal
function openCreateEventModal() {
  openModal("createEventModal");
}
async function submitCreateEvent() {
  const title = document.getElementById("newEvtTitle").value.trim();
  const event_type = document.getElementById("newEvtType").value;
  const city = document.getElementById("newEvtCity").value.trim();
  const event_date = document.getElementById("newEvtDate").value;
  const start_time = document.getElementById("newEvtStartTime").value;
  const duration_hours = parseFloat(document.getElementById("newEvtDuration").value);
  const setting = document.getElementById("newEvtSetting").value;
  const guest_count = parseInt(document.getElementById("newEvtGuests").value, 10);
  const budgetRs = parseFloat(document.getElementById("newEvtBudget").value);

  if (!title || !city || !event_date || isNaN(guest_count) || isNaN(budgetRs)) {
    showNotice("Please fill in all mandatory event fields.");
    return;
  }

  const dietaryEl = document.getElementById("newEvtDietary");
  const styleEl = document.getElementById("newEvtStyle");
  const dietary = dietaryEl ? dietaryEl.value : "standard";
  const style = styleEl ? styleEl.value : "royal";

  const payload = {
    title,
    event_type,
    city,
    event_date,
    start_time,
    duration_hours,
    timezone: "Asia/Kolkata",
    setting,
    guest_count,
    target_budget_paise: Math.round(budgetRs * 100),
    currency: "INR",
    contingency_bps: 1000,
    preferences: {
      dietary,
      style
    }
  };

  try {
    const res = await requestAPI("/api/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.success) {
      closeModal("createEventModal");
      await loadEvents();
      switchEvent(data.event_id);
    } else {
      showNotice("Error: " + (data.detail || "Failed to create event."));
    }
  } catch (e) {
    console.error("Create event error:", e);
    showNotice("Failed to create event.");
  }
}

// AI Quote Modal
function openQuoteModal() {
  openModal("quoteModal");
  document.getElementById("quoteReviewSection").style.display = "none";
  document.getElementById("btnApproveQuote").style.display = "none";
}
function loadSampleQuote(idx) {
  document.getElementById("rawQuoteInput").value = sampleQuotes[idx] || "";
}
async function parseQuoteAction() {
  const text = document.getElementById("rawQuoteInput").value.trim();
  if (!text) {
    showNotice("Please enter or paste vendor message text.");
    return;
  }
  const ind = document.getElementById("aiParserStatus");
  ind.textContent = "Extracting line items...";

  try {
    const res = await requestAPI(`/api/events/${currentEventId}/parse-quote`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ raw_quote_text: text })
    });
    const parsed = await res.json();
    ind.textContent = parsed.is_simulated ? "Basic parser · check every term before approval" : `AI-assisted · ${parsed.model_used || 'configured model'} · review before approval`;
    parsedQuoteData = parsed.data;

    document.getElementById("quoteReviewSection").style.display = "block";
    document.getElementById("btnApproveQuote").style.display = "inline-flex";

    document.getElementById("revVendorName").textContent = parsedQuoteData.vendor_name;
    document.getElementById("revCategory").textContent = parsedQuoteData.category;
    document.getElementById("revAdvance").textContent = formatPaise(parsedQuoteData.advance_deposit_paise);
    document.getElementById("revDueDate").textContent = parsedQuoteData.deposit_due_date || "Not specified";
    document.getElementById("revNegotiationReply").textContent = parsedQuoteData.suggested_negotiation_reply || "—";

    const tbody = document.getElementById("revItemsTableBody");
    tbody.innerHTML = "";
    parsedQuoteData.extracted_items.forEach(it => {
      const tr = el("tr", {}, [
        el("td", { style: { fontWeight: "600" } }, it.name),
        el("td", {}, it.pricing_model),
        el("td", { className: "numeric" }, formatPaise(it.unit_cost_paise)),
        el("td", { className: "numeric" }, `${it.tax_rate_bps / 100}%`)
      ]);
      tbody.appendChild(tr);
    });

    const flagBox = document.getElementById("revClausesBox");
    const flagList = document.getElementById("revClausesList");
    flagList.innerHTML = "";
    if (parsedQuoteData.explicit_clauses_extracted && parsedQuoteData.explicit_clauses_extracted.length > 0) {
      flagBox.style.display = "block";
      parsedQuoteData.explicit_clauses_extracted.forEach(cl => {
        flagList.appendChild(el("div", {}, `• ${cl}`));
      });
    } else {
      flagBox.style.display = "none";
    }

  } catch (e) {
    console.error("Quote parsing error:", e);
    ind.textContent = "Extraction failed.";
  }
}

async function approveQuoteAction() {
  if (!parsedQuoteData) return;
  try {
    const payload = {
      vendor_name: parsedQuoteData.vendor_name,
      category: parsedQuoteData.category,
      items: parsedQuoteData.extracted_items,
      advance_deposit_paise: parsedQuoteData.advance_deposit_paise,
      deposit_due_date: parsedQuoteData.deposit_due_date,
      notes: "Extracted and verified via Planqira",
      idempotency_key: `idem-${Date.now()}`
    };

    const res = await requestAPI(`/api/events/${currentEventId}/approve-quote`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await res.json();
    if (result.success) {
      showNotice(result.message);
      closeModal("quoteModal");
      await loadEventDetails(currentEventId);
    }
  } catch (e) {
    console.error("Approval error:", e);
    showNotice("Failed to approve quote.");
  }
}

// Record Payment Modal
function openRecordPaymentModal() {
  openModal("paymentModal");
}
async function submitRecordPayment() {
  const amtRs = parseFloat(document.getElementById("payAmountRs").value);
  const method = document.getElementById("payMethod").value;
  const note = document.getElementById("payReference").value.trim();

  if (isNaN(amtRs) || amtRs <= 0 || !note) {
    showNotice("Please enter a valid positive payment amount and reference note.");
    return;
  }

  try {
    const res = await requestAPI(`/api/events/${currentEventId}/record-payment`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        amount_paise: Math.round(amtRs * 100),
        payment_method: method,
        reference_note: note
      })
    });
    const data = await res.json();
    if (data.success) {
      showNotice(`Recorded actual cash payment of ₹${amtRs.toLocaleString('en-IN')}`);
      closeModal("paymentModal");
      await loadEventDetails(currentEventId);
    }
  } catch (e) {
    console.error("Payment error:", e);
    showNotice("Failed to record payment.");
  }
}

// Log Incident Modal
function openIncidentModal() {
  openModal("incidentModal");
}
async function submitIncident() {
  const severity = document.getElementById("incSeverity").value;
  const title = document.getElementById("incTitle").value.trim();
  const desc = document.getElementById("incDesc").value.trim();
  const resolution = document.getElementById("incResolution").value.trim();

  if (!title || !desc) {
    showNotice("Please provide incident title and operational description.");
    return;
  }

  try {
    const res = await requestAPI(`/api/events/${currentEventId}/incidents`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        severity,
        title,
        description: desc,
        resolution: resolution || null
      })
    });
    const data = await res.json();
    if (data.success) {
      closeModal("incidentModal");
      await loadEventDetails(currentEventId);
    }
  } catch (e) {
    console.error("Incident error:", e);
    showNotice("Failed to log incident.");
  }
}

// Revert Modal
function openRevertModal() {
  const picker = document.getElementById("revertVersionSelect");
  picker.innerHTML = "";
  (currentEventData.scenarios_history || []).forEach(sc => {
    if (sc.version < currentEventData.event.active_scenario_version) {
      const opt = document.createElement("option");
      opt.value = sc.version;
      opt.textContent = `Scenario v${sc.version} (${sc.name}) — ${sc.guest_count} Guests`;
      picker.appendChild(opt);
    }
  });

  if (picker.options.length === 0) {
    showNotice("No previous scenario versions available to revert to.");
    return;
  }
  openModal("revertModal");
}

async function submitRevert() {
  const version = parseInt(document.getElementById("revertVersionSelect").value, 10);
  const reason = document.getElementById("revertReasonInput").value.trim();

  if (!reason) {
    showNotice("Please state a concrete reason for reverting.");
    return;
  }

  try {
    const res = await requestAPI(`/api/events/${currentEventId}/revert-scenario`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target_version: version, reason })
    });
    const data = await res.json();
    if (data.success) {
      showNotice(`Created Scenario v${data.new_version} restoring state from v${version}. Payments and historical logs preserved.`);
      closeModal("revertModal");
      await loadEventDetails(currentEventId);
    }
  } catch (e) {
    console.error("Revert error:", e);
    showNotice("Failed to revert scenario.");
  }
}

// 8. Exports
function exportFile(format) {
  if (!currentEventId) return;
  window.location.href = `/api/events/${currentEventId}/export.${format}`;
}

// Startup
window.addEventListener("DOMContentLoaded", async () => {
  if (document.getElementById("eventSelector")) {
    initializeWorkspace();
    await Promise.allSettled([checkHealth(), loadEvents()]);
  }
});


function setWorkspaceLoading(loading, refreshing = false) {
  document.body.classList.toggle('is-loading', loading && !refreshing);
  document.body.classList.toggle('is-refreshing', loading && refreshing);
  document.getElementById('loadingState').hidden = !(loading && !refreshing);
  document.getElementById('dashboardContent').setAttribute('aria-busy', String(loading));
  // Prevent stale event actions while its data is changing.
  document.getElementById('workspaceMain').inert = loading;
  document.getElementById('refreshButton').disabled = loading;
  if (loading) {
    document.body.classList.remove('has-load-error', 'is-empty');
    document.getElementById('loadError').hidden = true;
    document.getElementById('emptyState').hidden = true;
    document.getElementById('syncStatus').textContent = refreshing ? 'Refreshing…' : 'Loading your plan…';
  }
}
function showLoadError(message) {
  setWorkspaceLoading(false);
  document.body.classList.add('has-load-error');
  document.getElementById('loadErrorText').textContent = message;
  document.getElementById('loadError').hidden = false;
  document.getElementById('syncStatus').textContent = 'Could not update';
}
async function refreshPlan() {
  if (currentEventId) await loadEventDetails(currentEventId);
  else await loadEvents();
  checkHealth();
}
function toggleSidebar(force) {
  const open = typeof force === 'boolean' ? force : document.body.classList.contains('sidebar-closed');
  document.body.classList.toggle('sidebar-closed', !open);
  const sidebar = document.getElementById('plannerSidebar');
  sidebar.inert = !open;
  sidebar.setAttribute('aria-hidden', String(!open));
  const button = document.getElementById('sidebarToggle');
  button.setAttribute('aria-expanded', String(open));
  button.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
  const mobile = matchMedia('(max-width: 760px)').matches;
  document.getElementById('sidebarBackdrop').hidden = !(open && mobile);
  document.getElementById('dashboardContent').inert = open && mobile;
  if (!open && sidebar.contains(document.activeElement)) button.focus();
  try { localStorage.setItem('planqira-navigation', open ? 'open' : 'closed'); } catch (_) {}
}
function showNotice(message) {
  document.getElementById('toastText').textContent = message;
  document.getElementById('toast').hidden = false;
}
function showDemoGuide() { openModal('guideModal'); }
function renderOverview(data) {
  const tasks = data.tasks || [];
  const done = tasks.filter(t => t.status === 'DONE').length;
  const pending = tasks.filter(t => t.status !== 'DONE').sort((a,b) => String(a.due_date || '').localeCompare(String(b.due_date || '')));
  const needsReview = tasks.filter(t => t.status === 'NEEDS_REVIEW').length;
  document.getElementById('taskProgress').max = Math.max(1, tasks.length);
  document.getElementById('taskProgress').value = done;
  document.getElementById('taskProgressCount').textContent = `${done} of ${tasks.length} complete`;
  const deficit = data.solvency.variance_paise < 0;
  document.getElementById('nextStepTitle').textContent = deficit ? 'Bring your plan within budget.' : needsReview ? 'A few details need another look.' : 'Turn your plan into a great day.';
  document.getElementById('nextStepDescription').textContent = deficit ? `Your plan is ${formatPaise(Math.abs(data.solvency.variance_paise))} over budget, including the emergency reserve. Review the largest costs or preview a change.` : needsReview ? `${needsReview} tasks need review after a change. Check these before confirming the next step.` : 'Check the next preparation tasks, then confirm the details with your vendors.';
  const next = document.getElementById('nextStepButton');
  next.textContent = deficit ? 'Review budget →' : 'Open checklist →';
  next.onclick = () => switchTab(deficit ? 'tabBudget' : 'tabTimeline');
  const list = document.getElementById('upcomingTasks'); list.replaceChildren();
  pending.slice(0,3).forEach(task => list.appendChild(el('div', {className:'task-preview'}, [el('span', {className:'task-dot', 'aria-hidden':'true'}), el('div', {}, [el('strong', {}, task.title || task.name || task.description || 'Planning task'), el('small', {}, `${task.due_date || 'No date set'} · ${task.status === 'NEEDS_REVIEW' ? 'Needs review' : 'To do'}`)])])));
  if (!pending.length) list.appendChild(el('p', {}, 'All preparation tasks are complete. Your event-day schedule is ready to review.'));
}
let simulationSequence = 0;
function invalidatePreview() {
  simulationSequence++;
  latestSimResult = null;
  ['simSummarySection', 'simDiffCard', 'simDagCallout'].forEach(id => document.getElementById(id).style.display = 'none');
}
function initializeWorkspace() {
  ['simSettingSelect', 'simDateInput'].forEach(id => document.getElementById(id).addEventListener('input', invalidatePreview));
  document.querySelectorAll('.table-clean').forEach(table => {
    if (table.parentElement.classList.contains('table-scroll')) return;
    const wrap = el('div', {className:'table-scroll', tabindex:'0', role:'region', 'aria-label':'Scrollable table'});
    table.before(wrap); wrap.appendChild(table);
  });
  document.querySelectorAll('.modal-overlay').forEach(modal => {
    const heading = modal.querySelector('h3');
    if (heading) { heading.id = `${modal.id}Title`; modal.setAttribute('aria-labelledby', heading.id); }
    modal.setAttribute('role', 'dialog'); modal.setAttribute('aria-modal', 'true');
    modal.querySelectorAll('button').forEach(b => { if (['✕','×'].includes(b.textContent.trim())) b.setAttribute('aria-label','Close dialog'); });
  });
  document.querySelectorAll('.form-label').forEach(label => {
    const control = label.parentElement.querySelector('input, select, textarea');
    if (control?.id) label.setAttribute('for', control.id);
  });
  let expanded = !matchMedia('(max-width: 760px)').matches;
  try { if (localStorage.getItem('planqira-navigation') === 'closed') expanded = false; } catch (_) {}
  toggleSidebar(expanded);
  switchTab(new URLSearchParams(location.search).get('tab') || 'tabOverview');
  matchMedia('(max-width: 760px)').addEventListener('change', e => toggleSidebar(!e.matches));
}
// Keep keyboard focus inside the active modal; Escape returns it to its trigger.
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && !document.querySelector('.modal-overlay.open')) toggleSidebar(false);
  if (event.key !== 'Tab') return;
  const modal = document.querySelector('.modal-overlay.open');
  if (!modal) return;
  const targets = [...modal.querySelectorAll('button, a[href], input, select, textarea, [tabindex="0"]')].filter(e => !e.disabled && e.getClientRects().length);
  const first = targets[0], last = targets[targets.length - 1];
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
});


async function requestAPI(url, options = {}) {
  const mutation = options.method && options.method !== 'GET';
  const trigger = mutation && document.activeElement instanceof HTMLButtonElement ? document.activeElement : null;
  const originalLabel = trigger?.textContent;
  if (trigger) { trigger.disabled = true; trigger.textContent = 'Working…'; trigger.setAttribute('aria-busy', 'true'); }
  try {
    const response = await fetch(url, {...options, signal: options.signal || AbortSignal.timeout(45000)});
    if (mutation && !response.ok) {
      const error = await response.clone().json().catch(() => ({}));
      throw new Error(typeof error.detail === 'string' ? error.detail : `Could not save this change (${response.status}). Please review the details and try again.`);
    }
    return response;
  } finally {
    if (trigger) { trigger.disabled = false; trigger.textContent = originalLabel; trigger.removeAttribute('aria-busy'); }
  }
}
