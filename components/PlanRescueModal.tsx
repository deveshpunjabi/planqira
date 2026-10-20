"use client";

import React, { useState } from "react";
import {
  Sparkles,
  Zap,
  TrendingUp,
  CloudRain,
  Edit3,
  X,
  AlertTriangle,
  ArrowRight,
  ShieldAlert,
  CheckCircle2,
} from "lucide-react";
import { formatCurrency } from "@/lib/budget";
import { applyProposal, generatePlanRescueProposal } from "@/lib/diff";
import {
  CurrencyCode,
  EventPlan,
  PlanRescueProposal,
  ReplanAction,
} from "@/lib/schema";

interface PlanRescueModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentPlan: EventPlan;
  onApplyPlan: (newPlan: EventPlan) => void;
}

export function PlanRescueModal({
  isOpen,
  onClose,
  currentPlan,
  onApplyPlan,
}: PlanRescueModalProps) {
  const [selectedAction, setSelectedAction] = useState<ReplanAction>("budget_cut_15");
  const [customInput, setCustomInput] = useState("");
  const [proposal, setProposal] = useState<PlanRescueProposal | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Generate initial proposal whenever modal opens or action changes
  React.useEffect(() => {
    if (isOpen) {
      setErrorMsg(null);
      const generated = generatePlanRescueProposal(currentPlan, selectedAction, customInput);
      setProposal(generated);
    }
  }, [isOpen, selectedAction, currentPlan, customInput]);

  const handleActionClick = (action: ReplanAction) => {
    setSelectedAction(action);
    setErrorMsg(null);
    const generated = generatePlanRescueProposal(
      currentPlan,
      action,
      action === "custom" ? customInput : undefined
    );
    setProposal(generated);
  };

  const handleCustomSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!customInput.trim()) return;
    setErrorMsg(null);
    const generated = generatePlanRescueProposal(currentPlan, "custom", customInput);
    setProposal(generated);
  };

  const handleApply = () => {
    if (!proposal) return;
    const result = applyProposal(currentPlan, proposal);
    if (!result.success) {
      setErrorMsg(result.error);
      return;
    }
    onApplyPlan(result.updatedPlan);
    onClose();
  };

  if (!isOpen) return null;

  const currency: CurrencyCode = currentPlan.budget.currency;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto no-print">
      <div className="bg-[#FCFAF6] rounded-3xl border border-[#EADBDE] shadow-2xl max-w-3xl w-full p-6 my-8 space-y-6 animate-in fade-in zoom-in-95 duration-150">
        {/* Modal Header */}
        <div className="flex items-center justify-between pb-3 border-b border-[#EADBDE]">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[#D97706] to-[#F59E0B] flex items-center justify-center text-white shadow-sm">
              <Zap className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-[#2B102B]">
                Plan Rescue & Crisis Re-Architect
              </h2>
              <p className="text-xs text-gray-600">
                Coordinated scenario replanning across themes, budget, timeline, and vendors with review gates.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-full hover:bg-gray-200 text-gray-500 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 4 Quick Mutation Action Triggers */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <button
            type="button"
            onClick={() => handleActionClick("budget_cut_15")}
            className={`p-3 rounded-2xl border text-left transition-all ${
              selectedAction === "budget_cut_15"
                ? "bg-amber-100 border-[#D97706] text-amber-950 font-bold shadow-sm"
                : "bg-white border-[#EADBDE] text-gray-700 hover:bg-gray-50"
            }`}
          >
            <div className="flex items-center gap-1.5 text-xs">
              <Zap className="w-3.5 h-3.5 text-[#D97706]" />
              <span>Squeeze 15%</span>
            </div>
            <div className="text-[10px] text-gray-500 mt-1">
              Prunes non-essentials; safeguards locked costs
            </div>
          </button>

          <button
            type="button"
            onClick={() => handleActionClick("guests_plus_25")}
            className={`p-3 rounded-2xl border text-left transition-all ${
              selectedAction === "guests_plus_25"
                ? "bg-amber-100 border-[#D97706] text-amber-950 font-bold shadow-sm"
                : "bg-white border-[#EADBDE] text-gray-700 hover:bg-gray-50"
            }`}
          >
            <div className="flex items-center gap-1.5 text-xs">
              <TrendingUp className="w-3.5 h-3.5 text-purple-600" />
              <span>Guests +25%</span>
            </div>
            <div className="text-[10px] text-gray-500 mt-1">
              Maintains fixed budget; shifts to buffet
            </div>
          </button>

          <button
            type="button"
            onClick={() => handleActionClick("rain_pivot")}
            className={`p-3 rounded-2xl border text-left transition-all ${
              selectedAction === "rain_pivot"
                ? "bg-amber-100 border-[#D97706] text-amber-950 font-bold shadow-sm"
                : "bg-white border-[#EADBDE] text-gray-700 hover:bg-gray-50"
            }`}
          >
            <div className="flex items-center gap-1.5 text-xs">
              <CloudRain className="w-3.5 h-3.5 text-blue-600" />
              <span>Rain Pivot</span>
            </div>
            <div className="text-[10px] text-gray-500 mt-1">
              Shelter protocol & indoor staging
            </div>
          </button>

          <button
            type="button"
            onClick={() => handleActionClick("custom")}
            className={`p-3 rounded-2xl border text-left transition-all ${
              selectedAction === "custom"
                ? "bg-amber-100 border-[#D97706] text-amber-950 font-bold shadow-sm"
                : "bg-white border-[#EADBDE] text-gray-700 hover:bg-gray-50"
            }`}
          >
            <div className="flex items-center gap-1.5 text-xs">
              <Edit3 className="w-3.5 h-3.5 text-emerald-600" />
              <span>Custom</span>
            </div>
            <div className="text-[10px] text-gray-500 mt-1">
              Custom user directive
            </div>
          </button>
        </div>

        {/* Custom Input (if Custom selected) */}
        {selectedAction === "custom" && (
          <form onSubmit={handleCustomSubmit} className="flex gap-2">
            <input
              type="text"
              value={customInput}
              onChange={(e) => setCustomInput(e.target.value)}
              placeholder="e.g. Cut DJ and reallocate funds into photography album"
              className="flex-1 text-xs rounded-xl border border-gray-300 px-3 py-2 text-gray-900 focus:border-[#D97706]"
            />
            <button
              type="submit"
              className="px-3 py-2 text-xs font-semibold bg-[#2B102B] text-white rounded-xl hover:bg-[#441D44]"
            >
              Update Proposal
            </button>
          </form>
        )}

        {/* Error message */}
        {errorMsg && (
          <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-red-800 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Before / After Diff Summary */}
        {proposal && (
          <div className="space-y-4">
            {/* Metric Comparison Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {/* Total Budget */}
              <div className="p-3 bg-white rounded-2xl border border-[#EADBDE] text-center">
                <span className="text-[10px] font-bold uppercase text-gray-500 block">
                  Total Budget
                </span>
                <div className="flex items-center justify-center gap-1.5 mt-1 font-mono text-xs">
                  <span className="text-gray-400 line-through">
                    {formatCurrency(proposal.diffSummary.oldTotalMinor, currency)}
                  </span>
                  <ArrowRight className="w-3 h-3 text-[#D97706]" />
                  <span className="font-bold text-[#2B102B]">
                    {formatCurrency(proposal.diffSummary.newTotalMinor, currency)}
                  </span>
                </div>
              </div>

              {/* 12% Reserve */}
              <div className="p-3 bg-white rounded-2xl border border-[#EADBDE] text-center">
                <span className="text-[10px] font-bold uppercase text-gray-500 block">
                  12% Buffer
                </span>
                <div className="flex items-center justify-center gap-1.5 mt-1 font-mono text-xs">
                  <span className="text-gray-400 line-through">
                    {formatCurrency(proposal.diffSummary.oldReserveMinor, currency)}
                  </span>
                  <ArrowRight className="w-3 h-3 text-[#D97706]" />
                  <span className="font-bold text-amber-900">
                    {formatCurrency(proposal.diffSummary.newReserveMinor, currency)}
                  </span>
                </div>
              </div>

              {/* Guest Count */}
              <div className="p-3 bg-white rounded-2xl border border-[#EADBDE] text-center">
                <span className="text-[10px] font-bold uppercase text-gray-500 block">
                  Guest Headcount
                </span>
                <div className="flex items-center justify-center gap-1.5 mt-1 font-mono text-xs">
                  <span className="text-gray-400">
                    {proposal.diffSummary.oldGuestCount}
                  </span>
                  <ArrowRight className="w-3 h-3 text-purple-600" />
                  <span className="font-bold text-purple-900">
                    {proposal.diffSummary.newGuestCount}
                  </span>
                </div>
              </div>

              {/* Per-Guest Allocation */}
              <div className="p-3 bg-white rounded-2xl border border-[#EADBDE] text-center">
                <span className="text-[10px] font-bold uppercase text-gray-500 block">
                  Per-Guest Allocation
                </span>
                <div className="flex items-center justify-center gap-1.5 mt-1 font-mono text-xs">
                  <span className="text-gray-400 line-through">
                    {formatCurrency(proposal.diffSummary.perGuestOldMinor * 100, currency)}
                  </span>
                  <ArrowRight className="w-3 h-3 text-[#D97706]" />
                  <span className="font-bold text-emerald-800">
                    {formatCurrency(proposal.diffSummary.perGuestNewMinor * 100, currency)}
                  </span>
                </div>
              </div>
            </div>

            {/* Infeasibility Alert / Deficit Gate */}
            {!proposal.tradeoffs.isFeasible && (
              <div className="p-4 rounded-2xl bg-red-50 border border-red-300 text-red-900 text-xs flex items-start gap-3">
                <ShieldAlert className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <div className="font-bold text-sm text-red-800">
                    Application Blocked: Infeasible Budget Proposal
                  </div>
                  <p>{proposal.tradeoffs.deficitWarning}</p>
                  <p className="font-semibold text-red-700">
                    This proposal cannot be applied to overwrite the accepted plan while in deficit.
                  </p>
                </div>
              </div>
            )}

            {/* 3 Explicit Tradeoff Explanations */}
            <div className="bg-white rounded-2xl border border-[#EADBDE] p-4 space-y-2">
              <span className="text-xs font-bold uppercase tracking-wider text-gray-700 block">
                Tradeoff Analysis & Operational Impacts
              </span>
              <ul className="space-y-1.5 text-xs text-gray-700">
                {proposal.tradeoffs.tradeoffs.map((item, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-[#D97706] font-bold">•</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Affected Tasks & Vendors */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="p-3 bg-[#FAF7F2] rounded-2xl border border-[#EADBDE] text-xs space-y-1">
                <span className="font-bold text-gray-700 block text-[11px] uppercase">
                  Milestone Revisions ({proposal.tradeoffs.affectedTasks.length})
                </span>
                {proposal.tradeoffs.affectedTasks.map((task, i) => (
                  <div key={i} className="text-gray-600 truncate">
                    • {task}
                  </div>
                ))}
              </div>

              <div className="p-3 bg-[#FAF7F2] rounded-2xl border border-[#EADBDE] text-xs space-y-1">
                <span className="font-bold text-gray-700 block text-[11px] uppercase">
                  Vendor Negotiations ({proposal.tradeoffs.vendorImpact.length})
                </span>
                {proposal.tradeoffs.vendorImpact.map((item, i) => (
                  <div key={i} className="text-gray-600 truncate">
                    • {item}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Modal Footer Controls */}
        <div className="flex items-center justify-between pt-3 border-t border-[#EADBDE]">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-gray-600 hover:text-gray-900 rounded-xl hover:bg-gray-100 transition-colors"
          >
            Cancel
          </button>

          <button
            type="button"
            disabled={!proposal || !proposal.tradeoffs.isFeasible}
            onClick={handleApply}
            className="px-5 py-2.5 text-xs sm:text-sm font-bold text-white bg-gradient-to-r from-[#2B102B] to-[#5D295D] rounded-xl hover:opacity-95 transition-all shadow-md disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <CheckCircle2 className="w-4 h-4 text-[#F59E0B]" />
            <span>Apply Changes (Rev #{currentPlan.metadata.revision + 1})</span>
          </button>
        </div>
      </div>
    </div>
  );
}
