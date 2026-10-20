import { describe, expect, it } from "vitest";
import {
  addDays,
  buildDayOfRunOfShow,
  buildPreparationTasks,
  diffDays,
  formatISODate,
  getTodayInTimezone,
  parseISODate,
} from "../lib/dates";

describe("Date and Timeline Engine Tests", () => {
  const timezone = "Asia/Kolkata";
  const today = getTodayInTimezone(timezone);

  it("calculates date differences and additions accurately", () => {
    const base = "2026-10-20";
    const nextDay = addDays(base, 1);
    expect(nextDay).toBe("2026-10-21");

    const sixtyDaysAhead = addDays(base, 60);
    expect(diffDays(base, sixtyDaysAhead)).toBe(60);
  });

  it("generates standard macro countdown for events with > 45 days lead time", () => {
    const eventDate = addDays(today, 60);
    const tasks = buildPreparationTasks("wedding", eventDate, timezone);

    expect(tasks.length).toBeGreaterThanOrEqual(5);
    const timeframes = tasks.map((t) => t.timeframe);
    expect(timeframes).toContain("T-60 Days");
    expect(timeframes).toContain("T-45 Days");
    expect(timeframes).toContain("T-1 Day");

    // All tasks must have valid due dates <= eventDate
    for (const task of tasks) {
      expect(task.dueDate <= eventDate).toBe(true);
    }
  });

  it("compresses preparation schedule for short-notice events (e.g. 3 days away)", () => {
    const eventDate = addDays(today, 3);
    const tasks = buildPreparationTasks("birthday", eventDate, timezone);

    // Should NOT include T-60 Days
    const timeframes = tasks.map((t) => t.timeframe);
    expect(timeframes).not.toContain("T-60 Days");
    expect(timeframes).toContain("T-3 Days");
    expect(timeframes).toContain("T-1 Day");
  });

  it("handles same-day and immediate events with same-day protocol", () => {
    const tasks = buildPreparationTasks("community", today, timezone);
    const timeframes = tasks.map((t) => t.timeframe);

    expect(timeframes[0]).toContain("T-Morning");
    expect(tasks.every((t) => t.dueDate === today)).toBe(true);
  });

  it("flags past-due tasks as overdue when due date precedes today and task is uncompleted", () => {
    // Generate tasks for an event 10 days away
    const eventDate = addDays(today, 10);
    const tasks = buildPreparationTasks("wedding", eventDate, timezone);

    // Any task whose dueDate < today must have isOverdue: true
    for (const task of tasks) {
      if (task.dueDate < today && !task.isCompleted) {
        expect(task.isOverdue).toBe(true);
      }
    }
  });

  it("generates valid chronological Day-Of run-of-show blocks", () => {
    const runOfShow = buildDayOfRunOfShow("wedding", "16:00", 6);
    expect(runOfShow.length).toBe(6);

    for (const block of runOfShow) {
      expect(block.timeSlot).toMatch(/^\d{2}:\d{2}\s*-\s*\d{2}:\d{2}$/);
      expect(block.frontOfHouseGuestView.length).toBeGreaterThan(0);
      expect(block.backOfHouseCrewAction.length).toBeGreaterThan(0);
      expect(block.leadVendorOrRole.length).toBeGreaterThan(0);
    }
  });
});
