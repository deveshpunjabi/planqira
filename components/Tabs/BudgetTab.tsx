"use client";

import React, { useState } from "react";
import {
  Coins,
  ShieldCheck,
  Lock,
  Unlock,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Lightbulb,
  Sliders,
} from "lucide-react";
import { formatCurrency } from "@/lib/budget";
import { BudgetCategory, BudgetPlan, CurrencyCode } from "@/lib/schema";

interface BudgetTabProps {
  budget: BudgetPlan;
  onUpdateTotalBudget: (newTotalMinor: number) => void;
  onToggleLockCategory: (categoryId: string) => void;
  onUpdateCategoryStatus: (categoryId: string, status: "planned" | "quoted" | "booked") => void;
}

const CATEGORY_COLORS: Record<string, string> = {
  "cat-venue": "#441D44",
  "cat-catering": "#7A397A",
  "cat-decor": "#D97706",
  "cat-entertainment": "#F59E0B",
  "cat-photo": "#0284C7",
  "cat-logistics": "#059669",
};

export function BudgetTab({
  budget,
  onUpdateTotalBudget,
  onToggleLockCategory,
  onUpdateCategoryStatus,
}: BudgetTabProps) {
  const [expandedCategories, setExpandedCategories] = useState<Record<string, boolean>>({});
  const [editTotalInput, setEditTotalInput] = useState<number>(Math.round(budget.totalMinor / 100));

  // Sync input when budget.totalMinor changes
  React.useEffect(() => {
    setEditTotalInput(Math.round(budget.totalMinor / 100));
  }, [budget.totalMinor]);

  const toggleCategoryExpand = (id: string) => {
    setExpandedCategories((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleTotalSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onUpdateTotalBudget(Math.max(100, Math.round(editTotalInput * 100)));
  };

  return (
    <div className="space-y-6">
      {/* Tab Header & Recalculator */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-2 border-b border-[#EADBDE]">
        <div>
          <h2 className="text-lg font-bold text-[#2B102B] flex items-center gap-2">
            <Coins className="w-5 h-5 text-[#D97706]" />
            Deterministic Budget Ledger & Contingency Engine
          </h2>
          <p className="text-xs text-gray-600">
            Integer minor units, 12% locked emergency reserve, and real-time locked-cost rebalancing.
          </p>
        </div>

        {/* Real-time What-If Budget Recalculator */}
        <form
          onSubmit={handleTotalSubmit}
          className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-xl border border-[#EADBDE] shadow-sm"
        >
          <Sliders className="w-4 h-4 text-[#D97706]" />
          <span className="text-xs font-semibold text-gray-700 whitespace-nowrap">
            Recalculate Total:
          </span>
          <div className="flex items-center">
            <span className="text-xs font-bold text-gray-500 mr-1">
              {budget.currency === "INR" ? "₹" : budget.currency === "USD" ? "$" : "€"}
            </span>
            <input
              type="number"
              min={100}
              value={editTotalInput}
              onChange={(e) => setEditTotalInput(Number(e.target.value))}
              className="w-28 text-xs font-bold text-[#2B102B] rounded border border-gray-300 px-2 py-1 focus:border-[#D97706]"
            />
          </div>
          <button
            type="submit"
            className="text-xs font-semibold px-2.5 py-1 bg-[#2B102B] text-white rounded-lg hover:bg-[#441D44] transition-colors"
          >
            Apply
          </button>
        </form>
      </div>

      {/* Infeasibility / Deficit Alert Banner */}
      {budget.isDeficit && (
        <div className="rounded-xl border border-red-300 bg-red-50 p-4 text-red-900 flex items-start gap-3 shadow-sm">
          <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <div className="font-bold text-sm text-red-800">
              Budget Infeasibility Deficit Detected
            </div>
            <div>{budget.deficitReason}</div>
            <div className="font-semibold text-red-700">
              Required action: Unlock one or more locked categories or increase the total budget to rebalance the ledger.
            </div>
          </div>
        </div>
      )}

      {/* 12% Contingency Buffer Card & Macro Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Total Budget Card */}
        <div className="bg-white rounded-2xl p-4 border border-[#EADBDE] shadow-sm">
          <div className="text-xs text-gray-500 uppercase font-semibold">
            Total Event Budget
          </div>
          <div className="text-2xl font-black text-[#2B102B] mt-1">
            {formatCurrency(budget.totalMinor, budget.currency)}
          </div>
          <div className="text-xs text-gray-600 mt-1">
            Allocated across 6 pillars + 12% emergency reserve
          </div>
        </div>

        {/* 12% Contingency Card */}
        <div className="bg-gradient-to-br from-amber-50 to-amber-100/70 rounded-2xl p-4 border border-amber-300 shadow-sm md:col-span-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-xs font-bold text-amber-950 uppercase tracking-wide">
              <ShieldCheck className="w-4 h-4 text-[#D97706]" />
              Locked 12% Emergency & Hidden-Fee Buffer
            </div>
            <span className="text-xs font-mono font-bold bg-amber-200/80 text-amber-900 px-2 py-0.5 rounded-full">
              Strict 12.0% Rule
            </span>
          </div>
          <div className="text-2xl font-black text-amber-950 mt-1">
            {formatCurrency(budget.reserveMinor, budget.currency)}
          </div>
          <p className="text-xs text-amber-900/80 mt-1">
            Safeguards against surprise vendor overtime, corkage surcharges, weather emergency tenting, and last-minute municipal fee hikes.
          </p>
        </div>
      </div>

      {/* Visual Horizontal Stacked Percentage Bar */}
      <div className="bg-white p-4 rounded-2xl border border-[#EADBDE] shadow-sm space-y-2">
        <div className="flex items-center justify-between text-xs font-semibold text-gray-700">
          <span>Allocation Spectrum</span>
          <span>
            {formatCurrency(budget.allocatableMinor, budget.currency)} (88%) +{" "}
            {formatCurrency(budget.reserveMinor, budget.currency)} (12% Reserve)
          </span>
        </div>

        <div className="h-5 rounded-xl overflow-hidden flex shadow-inner bg-gray-100">
          {budget.categories.map((cat) => (
            <div
              key={cat.id}
              style={{
                width: `${cat.percentage}%`,
                backgroundColor: CATEGORY_COLORS[cat.id] || "#7A397A",
              }}
              className="h-full relative group transition-all"
              title={`${cat.name}: ${cat.percentage}% (${formatCurrency(cat.amountMinor, budget.currency)})`}
            />
          ))}
          {/* 12% Reserve slice */}
          <div
            style={{ width: "12%", backgroundColor: "#D97706" }}
            className="h-full relative group transition-all"
            title={`12% Reserve: ${formatCurrency(budget.reserveMinor, budget.currency)}`}
          />
        </div>

        {/* Legend */}
        <div className="flex flex-wrap items-center gap-3 pt-1 text-[11px] text-gray-600">
          {budget.categories.map((cat) => (
            <div key={cat.id} className="flex items-center gap-1.5">
              <span
                className="w-2.5 h-2.5 rounded-full"
                style={{ backgroundColor: CATEGORY_COLORS[cat.id] || "#7A397A" }}
              />
              <span>
                {cat.name.split("&")[0].trim()} ({cat.percentage}%)
              </span>
            </div>
          ))}
          <div className="flex items-center gap-1.5 font-semibold text-amber-900">
            <span className="w-2.5 h-2.5 rounded-full bg-[#D97706]" />
            <span>Emergency Buffer (12%)</span>
          </div>
        </div>
      </div>

      {/* 6 Category Ledger Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {budget.categories.map((category) => {
          const isExpanded = expandedCategories[category.id] ?? false;

          return (
            <div
              key={category.id}
              className={`bg-white rounded-2xl border p-4 shadow-sm transition-all ${
                category.isLocked
                  ? "border-amber-300 ring-1 ring-amber-300/50 bg-amber-50/20"
                  : "border-[#EADBDE] hover:border-gray-300"
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-bold text-[#2B102B] text-sm">
                      {category.name}
                    </h3>
                    <span className="text-[11px] font-mono text-gray-500 font-semibold bg-gray-100 px-1.5 py-0.2 rounded">
                      {category.percentage}%
                    </span>
                  </div>
                  <div className="text-lg font-black text-[#2B102B] mt-0.5">
                    {formatCurrency(category.amountMinor, budget.currency)}
                  </div>
                </div>

                {/* Status & Lock Controls */}
                <div className="flex items-center gap-1.5">
                  <select
                    value={category.status}
                    onChange={(e) =>
                      onUpdateCategoryStatus(
                        category.id,
                        e.target.value as "planned" | "quoted" | "booked"
                      )
                    }
                    className="text-[10px] font-semibold rounded-md border border-gray-300 bg-white px-2 py-1 text-gray-700"
                  >
                    <option value="planned">Planned</option>
                    <option value="quoted">Quoted</option>
                    <option value="booked">Booked</option>
                  </select>

                  <button
                    type="button"
                    onClick={() => onToggleLockCategory(category.id)}
                    className={`p-1.5 rounded-lg border transition-colors ${
                      category.isLocked
                        ? "bg-amber-100 text-amber-900 border-amber-300"
                        : "bg-gray-50 text-gray-500 border-gray-200 hover:bg-gray-100"
                    }`}
                    title={
                      category.isLocked
                        ? "Locked: Cost preserved during budget replan"
                        : "Unlocked: Floats dynamically with budget changes"
                    }
                  >
                    {category.isLocked ? (
                      <Lock className="w-3.5 h-3.5 text-amber-700" />
                    ) : (
                      <Unlock className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>
              </div>

              {/* Line Items Accordion */}
              <div className="mt-3 pt-3 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => toggleCategoryExpand(category.id)}
                  className="w-full flex items-center justify-between text-xs font-semibold text-gray-600 hover:text-gray-900"
                >
                  <span>Itemized Breakdown ({category.lineItems.length} items)</span>
                  {isExpanded ? (
                    <ChevronUp className="w-3.5 h-3.5" />
                  ) : (
                    <ChevronDown className="w-3.5 h-3.5" />
                  )}
                </button>

                {isExpanded && (
                  <div className="mt-2 space-y-1.5 bg-[#FCFAF6] p-2 rounded-xl border border-[#EADBDE]">
                    {category.lineItems.map((item) => (
                      <div
                        key={item.id}
                        className="flex items-center justify-between text-xs text-gray-700 py-0.5 border-b border-gray-100 last:border-none"
                      >
                        <span className="truncate pr-2">{item.name}</span>
                        <span className="font-mono font-medium whitespace-nowrap">
                          {formatCurrency(item.amountMinor, budget.currency)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Negotiation Cost-Saving Hack */}
              <div className="mt-3 p-2 rounded-xl bg-amber-50/70 border border-amber-200/80 text-[11px] text-amber-950 flex items-start gap-1.5">
                <Lightbulb className="w-3.5 h-3.5 text-[#D97706] mt-0.5 flex-shrink-0" />
                <div>
                  <span className="font-semibold text-amber-900">Cost-Saving Hack: </span>
                  {category.costSavingHack}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
