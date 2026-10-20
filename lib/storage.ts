import { EventPlan, EventPlanSchema } from "./schema";

const STORAGE_KEY = "utsav_ai_active_plan_v1";
const UNDO_STORAGE_KEY = "utsav_ai_undo_history_v1";

export function isLocalStorageAvailable(): boolean {
  if (typeof window === "undefined") return false;
  try {
    const testKey = "__utsav_storage_test__";
    window.localStorage.setItem(testKey, "1");
    window.localStorage.removeItem(testKey);
    return true;
  } catch {
    return false;
  }
}

export function saveActivePlan(plan: EventPlan): { success: boolean; error?: string } {
  if (!isLocalStorageAvailable()) {
    return { success: false, error: "Local storage is not accessible in this browser context." };
  }
  try {
    const serialized = JSON.stringify(plan);
    window.localStorage.setItem(STORAGE_KEY, serialized);
    return { success: true };
  } catch (err) {
    const msg = err instanceof Error ? err.message : "Failed to save plan to browser storage";
    return { success: false, error: msg };
  }
}

export function loadActivePlan(): EventPlan | null {
  if (!isLocalStorageAvailable()) return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    const result = EventPlanSchema.safeParse(parsed);
    if (result.success) {
      return result.data;
    }
    return null;
  } catch {
    return null;
  }
}

export function pushUndoHistory(plan: EventPlan): void {
  if (!isLocalStorageAvailable()) return;
  try {
    const raw = window.localStorage.getItem(UNDO_STORAGE_KEY);
    const history: EventPlan[] = raw ? JSON.parse(raw) : [];
    history.push(JSON.parse(JSON.stringify(plan)));
    // Keep last 5 snapshots to avoid storage quota issues
    const trimmed = history.slice(-5);
    window.localStorage.setItem(UNDO_STORAGE_KEY, JSON.stringify(trimmed));
  } catch {
    // Graceful ignore
  }
}

export function popUndoHistory(): EventPlan | null {
  if (!isLocalStorageAvailable()) return null;
  try {
    const raw = window.localStorage.getItem(UNDO_STORAGE_KEY);
    if (!raw) return null;
    const history: EventPlan[] = JSON.parse(raw);
    if (history.length === 0) return null;
    const previous = history.pop();
    window.localStorage.setItem(UNDO_STORAGE_KEY, JSON.stringify(history));
    return previous || null;
  } catch {
    return null;
  }
}

export function exportPlanAsJSON(plan: EventPlan): void {
  if (typeof window === "undefined") return;
  try {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(plan, null, 2));
    const downloadAnchor = document.createElement("a");
    const sanitizedTitle = (plan.brief.title || "utsav-event").toLowerCase().replace(/[^a-z0-9]/g, "-");
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `${sanitizedTitle}-blueprint-v${plan.metadata.revision}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  } catch (err) {
    console.error("Export failed:", err);
  }
}

export function importPlanFromJSON(
  jsonContent: string
): { success: true; plan: EventPlan } | { success: false; error: string } {
  try {
    const parsed = JSON.parse(jsonContent);
    const validation = EventPlanSchema.safeParse(parsed);
    if (!validation.success) {
      const firstIssue = validation.error.issues[0];
      return {
        success: false,
        error: `Invalid plan schema: ${firstIssue?.path.join(".")} - ${firstIssue?.message}`,
      };
    }

    const plan = validation.data;
    if (plan.metadata.schemaVersion !== 1) {
      return {
        success: false,
        error: `Unsupported schema version: ${plan.metadata.schemaVersion}. Expected version 1.`,
      };
    }

    // Verify budget mathematical integrity
    const expectedReserve = Math.round((plan.budget.totalMinor * 12) / 100);
    if (Math.abs(plan.budget.reserveMinor - expectedReserve) > 1) {
      return {
        success: false,
        error: `Corrupt budget math: Reserve (${plan.budget.reserveMinor}) does not match 12% contingency (${expectedReserve}).`,
      };
    }

    return {
      success: true,
      plan,
    };
  } catch {
    return {
      success: false,
      error: "Malformed JSON file. Please check file format.",
    };
  }
}
