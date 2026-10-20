"use client";

import React, { useEffect, useState } from "react";
import {
  Palette,
  Coins,
  Calendar,
  Briefcase,
  Zap,
  Sparkles,
  AlertCircle,
  X,
  FileCheck,
} from "lucide-react";
import { BriefForm } from "@/components/BriefForm";
import { Header } from "@/components/Header";
import { PlanRescueModal } from "@/components/PlanRescueModal";
import { BudgetTab } from "@/components/Tabs/BudgetTab";
import { IdeasTab } from "@/components/Tabs/IdeasTab";
import { TimelineTab } from "@/components/Tabs/TimelineTab";
import { VendorsTab } from "@/components/Tabs/VendorsTab";
import {
  DEFAULT_PLAN,
  SAMPLE_BIRTHDAY_PLAN,
  SAMPLE_COMMUNITY_PLAN,
  SAMPLE_GALA_PLAN,
  SAMPLE_PLANS,
  SAMPLE_WEDDING_PLAN,
} from "@/data/sample-plans";
import { calculateBudget, formatCurrency } from "@/lib/budget";
import { restorePlanWithFreshRevision } from "@/lib/diff";
import {
  EventBrief,
  EventPlan,
} from "@/lib/schema";
import {
  exportPlanAsJSON,
  importPlanFromJSON,
  loadActivePlan,
  popUndoHistory,
  pushUndoHistory,
  saveActivePlan,
} from "@/lib/storage";

export default function Home() {
  const [activePlan, setActivePlan] = useState<EventPlan>(DEFAULT_PLAN);
  const [activeTab, setActiveTab] = useState<"ideas" | "budget" | "timeline" | "vendors">("ideas");
  const [isGenerating, setIsGenerating] = useState(false);
  const [isPlanRescueOpen, setIsPlanRescueOpen] = useState(false);
  const [canUndo, setCanUndo] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Initialize from localStorage or fallback to SAMPLE_WEDDING_PLAN
  useEffect(() => {
    const saved = loadActivePlan();
    if (saved) {
      setActivePlan(saved);
    }
  }, []);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  // Helper to update activePlan with persistence and undo tracking
  const updatePlan = (
    newPlan: EventPlan,
    trackUndo = true,
    markEdited = true,
    toastText?: string
  ) => {
    if (trackUndo) {
      pushUndoHistory(activePlan);
      setCanUndo(true);
    }

    const finalized: EventPlan = {
      ...newPlan,
      metadata: {
        ...newPlan.metadata,
        source: markEdited && newPlan.metadata.source === "live-ai" ? "locally-edited" : newPlan.metadata.source,
        updatedAt: new Date().toISOString(),
      },
    };

    setActivePlan(finalized);
    saveActivePlan(finalized);
    if (toastText) showToast(toastText);
  };

  // Preset Selection
  const handleSelectPreset = (presetKey: string) => {
    const preset = SAMPLE_PLANS[presetKey];
    if (preset) {
      updatePlan(
        JSON.parse(JSON.stringify(preset)),
        true,
        false,
        `Loaded preset: ${preset.brief.title}`
      );
    }
  };

  // Brief Form Generation (calls /api/plan)
  const handleGeneratePlan = async (brief: EventBrief) => {
    setIsGenerating(true);
    setErrorMessage(null);

    try {
      const response = await fetch("/api/plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ brief }),
      });

      const data = await response.json();

      if (!response.ok || !data.success) {
        const errorText = data.error || "Failed to generate plan via AI.";
        setErrorMessage(errorText);
        showToast("AI Generation Failed: Keeping current plan intact.");
        return;
      }

      // Valid live AI plan returned
      updatePlan(data.plan, true, false, "Live AI Blueprint successfully generated!");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Network error during plan generation.";
      setErrorMessage(msg);
      showToast("Network error: Preserved current plan.");
    } finally {
      setIsGenerating(false);
    }
  };

  // Total budget update (What-If calculator)
  const handleUpdateTotalBudget = (newTotalMinor: number) => {
    const budgetRes = calculateBudget(newTotalMinor, activePlan.budget.categories);
    const updated: EventPlan = {
      ...activePlan,
      metadata: {
        ...activePlan.metadata,
        revision: activePlan.metadata.revision + 1,
        source: "locally-edited",
      },
      brief: {
        ...activePlan.brief,
        totalBudget: newTotalMinor,
      },
      budget: {
        ...budgetRes,
        currency: activePlan.budget.currency,
      },
    };
    updatePlan(updated, true, true, "Recalculated budget and rebalanced allocations.");
  };

  // Category Lock Toggle
  const handleToggleLockCategory = (categoryId: string) => {
    const updatedCategories = activePlan.budget.categories.map((c) =>
      c.id === categoryId ? { ...c, isLocked: !c.isLocked } : c
    );
    const budgetRes = calculateBudget(activePlan.budget.totalMinor, updatedCategories);
    const updated: EventPlan = {
      ...activePlan,
      metadata: {
        ...activePlan.metadata,
        revision: activePlan.metadata.revision + 1,
        source: "locally-edited",
      },
      budget: {
        ...budgetRes,
        currency: activePlan.budget.currency,
      },
    };
    updatePlan(updated, true, true, "Updated category lock state.");
  };

  // Category Status Update
  const handleUpdateCategoryStatus = (
    categoryId: string,
    status: "planned" | "quoted" | "booked"
  ) => {
    const updatedCategories = activePlan.budget.categories.map((c) =>
      c.id === categoryId ? { ...c, status } : c
    );
    const updated: EventPlan = {
      ...activePlan,
      budget: {
        ...activePlan.budget,
        categories: updatedCategories,
      },
    };
    updatePlan(updated, false, true);
  };

  // Theme selection
  const handleSelectTheme = (themeId: string) => {
    const updated: EventPlan = {
      ...activePlan,
      selectedThemeId: themeId,
    };
    updatePlan(updated, true, true, "Active theme updated.");
  };

  // Timeline task completion toggle
  const handleToggleTaskCompletion = (taskId: string) => {
    const updatedTasks = activePlan.timeline.preparationTasks.map((t) =>
      t.id === taskId ? { ...t, isCompleted: !t.isCompleted } : t
    );
    const updated: EventPlan = {
      ...activePlan,
      timeline: {
        ...activePlan.timeline,
        preparationTasks: updatedTasks,
      },
    };
    updatePlan(updated, false, true);
  };

  // Vendor contract checklist toggle
  const handleToggleVendorChecklist = (vendorId: string, itemId: string) => {
    const updatedVendors = activePlan.vendors.map((v) => {
      if (v.id === vendorId) {
        return {
          ...v,
          contractChecklist: v.contractChecklist.map((c) =>
            c.id === itemId ? { ...c, checked: !c.checked } : c
          ),
        };
      }
      return v;
    });
    const updated: EventPlan = {
      ...activePlan,
      vendors: updatedVendors,
    };
    updatePlan(updated, false, true);
  };

  // Vendor status update
  const handleUpdateVendorStatus = (
    vendorId: string,
    status: "not-started" | "inquiry-sent" | "quote-received" | "booked"
  ) => {
    const updatedVendors = activePlan.vendors.map((v) =>
      v.id === vendorId ? { ...v, status } : v
    );
    const updated: EventPlan = {
      ...activePlan,
      vendors: updatedVendors,
    };
    updatePlan(updated, false, true);
  };

  // Vendor notes update
  const handleUpdateVendorNotes = (vendorId: string, notes: string) => {
    const updatedVendors = activePlan.vendors.map((v) =>
      v.id === vendorId ? { ...v, notes } : v
    );
    const updated: EventPlan = {
      ...activePlan,
      vendors: updatedVendors,
    };
    updatePlan(updated, false, true);
  };

  // Undo Handler
  const handleUndo = () => {
    const previous = popUndoHistory();
    if (previous) {
      const restored = restorePlanWithFreshRevision(activePlan.metadata.revision, previous);
      setActivePlan(restored);
      saveActivePlan(restored);
      showToast(`Restored previous state as Rev #${restored.metadata.revision}`);
    } else {
      setCanUndo(false);
      showToast("No further undo snapshots available.");
    }
  };

  // Export JSON
  const handleExport = () => {
    exportPlanAsJSON(activePlan);
    showToast("Downloaded event blueprint JSON backup.");
  };

  // Import JSON
  const handleImport = (jsonString: string) => {
    const res = importPlanFromJSON(jsonString);
    if (!res.success) {
      setErrorMessage(res.error);
      showToast("Import failed: check file format.");
      return;
    }
    updatePlan(res.plan, true, false, `Imported blueprint: ${res.plan.brief.title}`);
  };

  // Print
  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#FCFAF6]">
      {/* Global Header */}
      <Header
        plan={activePlan}
        onExportPlan={handleExport}
        onImportPlan={handleImport}
        onPrintPlan={handlePrint}
        onUndo={handleUndo}
        canUndo={canUndo}
      />

      {/* Ephemeral Toast Alert */}
      {toastMessage && (
        <div className="fixed bottom-5 right-5 z-50 bg-[#2B102B] text-white text-xs font-semibold px-4 py-2.5 rounded-xl shadow-xl flex items-center gap-2 border border-purple-800 animate-in fade-in slide-in-from-bottom-2 duration-200 no-print">
          <FileCheck className="w-4 h-4 text-[#F59E0B]" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
        {/* Error Notification Banner */}
        {errorMessage && (
          <div className="bg-red-50 border border-red-300 rounded-2xl p-4 text-red-900 text-xs flex items-start justify-between gap-3 shadow-sm no-print">
            <div className="flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <div className="font-bold text-red-800">Generation Error</div>
                <div className="mt-0.5">{errorMessage}</div>
                <div className="text-gray-600 mt-1">
                  Your existing accepted plan and all local edits have been preserved. You can continue editing or use the sample blueprints.
                </div>
              </div>
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-gray-400 hover:text-gray-700 p-1"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Top Summary Banner */}
        <section className="bg-gradient-to-r from-[#2B102B] via-[#441D44] to-[#5D295D] rounded-3xl p-6 sm:p-8 text-white shadow-md relative overflow-hidden">
          <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            <div className="space-y-2">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs uppercase font-bold tracking-widest text-[#F59E0B] bg-white/10 px-3 py-1 rounded-full backdrop-blur-sm">
                  {activePlan.brief.eventType.toUpperCase()} BLUEPRINT
                </span>
                <span className="text-xs text-gray-300">
                  {activePlan.brief.setting.toUpperCase()} SETTING
                </span>
              </div>
              <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-white">
                {activePlan.brief.title}
              </h1>
              <p className="text-xs sm:text-sm text-gray-200 max-w-2xl leading-relaxed">
                {activePlan.brief.city} • {activePlan.brief.eventDate} ({activePlan.brief.startTime},{" "}
                {activePlan.brief.durationHours}h) • {activePlan.brief.guestCount} Guests
              </p>
            </div>

            {/* Quick Metrics and Plan Rescue Action */}
            <div className="flex flex-wrap items-center gap-3 self-start lg:self-auto no-print">
              <div className="bg-white/10 backdrop-blur-md rounded-2xl p-3 border border-white/10 text-center min-w-[120px]">
                <div className="text-[10px] uppercase font-bold text-gray-300">Total Budget</div>
                <div className="text-lg font-black text-white">
                  {formatCurrency(activePlan.budget.totalMinor, activePlan.budget.currency)}
                </div>
              </div>

              <div className="bg-white/10 backdrop-blur-md rounded-2xl p-3 border border-white/10 text-center min-w-[120px]">
                <div className="text-[10px] uppercase font-bold text-[#F59E0B]">12% Reserve</div>
                <div className="text-lg font-black text-[#FCD34D]">
                  {formatCurrency(activePlan.budget.reserveMinor, activePlan.budget.currency)}
                </div>
              </div>

              {/* Instant Plan Rescue Trigger Button */}
              <button
                type="button"
                onClick={() => setIsPlanRescueOpen(true)}
                className="px-4 py-3 rounded-2xl bg-gradient-to-r from-[#D97706] to-[#F59E0B] text-white font-bold text-xs sm:text-sm hover:opacity-95 transition-all shadow-lg flex items-center gap-2 self-stretch sm:self-auto"
              >
                <Zap className="w-4 h-4 fill-white text-white" />
                <span>Launch Plan Rescue</span>
              </button>
            </div>
          </div>
        </section>

        {/* 2-Column Main Workspace */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left Column: Brief Deck (Desktop sticky, Mobile stacked) */}
          <div className="lg:col-span-4 no-print">
            <div className="lg:sticky lg:top-20 space-y-4">
              <BriefForm
                brief={activePlan.brief}
                onUpdateBrief={(b) => {
                  setActivePlan((prev) => ({ ...prev, brief: b }));
                }}
                onGeneratePlan={handleGeneratePlan}
                onSelectPreset={handleSelectPreset}
                isGenerating={isGenerating}
              />
            </div>
          </div>

          {/* Right Column: 4 Core Planning Pillars */}
          <div className="lg:col-span-8 space-y-6">
            {/* Tab Navigation Deck */}
            <div className="flex bg-[#F8F4EC] p-1.5 rounded-2xl border border-[#EADBDE] overflow-x-auto no-print">
              <button
                type="button"
                onClick={() => setActiveTab("ideas")}
                className={`flex-1 min-w-[110px] py-2.5 px-3 rounded-xl text-xs sm:text-sm font-bold flex items-center justify-center gap-2 transition-all ${
                  activeTab === "ideas"
                    ? "bg-white text-[#2B102B] shadow-sm"
                    : "text-gray-600 hover:text-gray-900"
                }`}
              >
                <Palette className="w-4 h-4 text-[#D97706]" />
                <span>1. Themes</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab("budget")}
                className={`flex-1 min-w-[110px] py-2.5 px-3 rounded-xl text-xs sm:text-sm font-bold flex items-center justify-center gap-2 transition-all ${
                  activeTab === "budget"
                    ? "bg-white text-[#2B102B] shadow-sm"
                    : "text-gray-600 hover:text-gray-900"
                }`}
              >
                <Coins className="w-4 h-4 text-[#D97706]" />
                <span>2. Budget</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab("timeline")}
                className={`flex-1 min-w-[110px] py-2.5 px-3 rounded-xl text-xs sm:text-sm font-bold flex items-center justify-center gap-2 transition-all ${
                  activeTab === "timeline"
                    ? "bg-white text-[#2B102B] shadow-sm"
                    : "text-gray-600 hover:text-gray-900"
                }`}
              >
                <Calendar className="w-4 h-4 text-[#D97706]" />
                <span>3. Timeline</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab("vendors")}
                className={`flex-1 min-w-[110px] py-2.5 px-3 rounded-xl text-xs sm:text-sm font-bold flex items-center justify-center gap-2 transition-all ${
                  activeTab === "vendors"
                    ? "bg-white text-[#2B102B] shadow-sm"
                    : "text-gray-600 hover:text-gray-900"
                }`}
              >
                <Briefcase className="w-4 h-4 text-[#D97706]" />
                <span>4. Vendors</span>
              </button>
            </div>

            {/* Active Tab Component Render (Screen) */}
            <div className="no-print">
              {activeTab === "ideas" && (
                <IdeasTab
                  themes={activePlan.themes}
                  selectedThemeId={activePlan.selectedThemeId}
                  onSelectTheme={handleSelectTheme}
                />
              )}

              {activeTab === "budget" && (
                <BudgetTab
                  budget={activePlan.budget}
                  onUpdateTotalBudget={handleUpdateTotalBudget}
                  onToggleLockCategory={handleToggleLockCategory}
                  onUpdateCategoryStatus={handleUpdateCategoryStatus}
                />
              )}

              {activeTab === "timeline" && (
                <TimelineTab
                  preparationTasks={activePlan.timeline.preparationTasks}
                  dayOfRunOfShow={activePlan.timeline.dayOfRunOfShow}
                  onToggleTaskCompletion={handleToggleTaskCompletion}
                  eventDate={activePlan.brief.eventDate}
                />
              )}

              {activeTab === "vendors" && (
                <VendorsTab
                  vendors={activePlan.vendors}
                  onToggleChecklistItem={handleToggleVendorChecklist}
                  onUpdateVendorStatus={handleUpdateVendorStatus}
                  onUpdateVendorNotes={handleUpdateVendorNotes}
                />
              )}
            </div>

            {/* Print-Only Multi-Pillar Section (Included in window.print()) */}
            <div className="hidden print:block space-y-8">
              <div className="border-b pb-4">
                <h1 className="text-2xl font-black">{activePlan.brief.title}</h1>
                <p className="text-sm text-gray-600">
                  {activePlan.brief.city} • {activePlan.brief.eventDate} • {activePlan.brief.guestCount} Guests
                </p>
                <p className="text-xs text-gray-500 font-mono mt-1">
                  Source: {activePlan.metadata.source} | Revision #{activePlan.metadata.revision} | Created with UtsavAI
                </p>
              </div>

              {/* Pillar 1: Themes */}
              <div className="space-y-4">
                <h2 className="text-lg font-bold border-b pb-1">1. Curated Themes</h2>
                <IdeasTab
                  themes={activePlan.themes}
                  selectedThemeId={activePlan.selectedThemeId}
                  onSelectTheme={() => {}}
                />
              </div>

              {/* Pillar 2: Budget */}
              <div className="space-y-4 page-break">
                <h2 className="text-lg font-bold border-b pb-1">2. Complete Budget Ledger</h2>
                <BudgetTab
                  budget={activePlan.budget}
                  onUpdateTotalBudget={() => {}}
                  onToggleLockCategory={() => {}}
                  onUpdateCategoryStatus={() => {}}
                />
              </div>

              {/* Pillar 3: Timeline */}
              <div className="space-y-4 page-break">
                <h2 className="text-lg font-bold border-b pb-1">3. Timeline & Day-Of Run of Show</h2>
                <TimelineTab
                  preparationTasks={activePlan.timeline.preparationTasks}
                  dayOfRunOfShow={activePlan.timeline.dayOfRunOfShow}
                  onToggleTaskCompletion={() => {}}
                  eventDate={activePlan.brief.eventDate}
                />
              </div>

              {/* Pillar 4: Vendors */}
              <div className="space-y-4 page-break">
                <h2 className="text-lg font-bold border-b pb-1">4. Vendor Interrogation Kit</h2>
                <VendorsTab
                  vendors={activePlan.vendors}
                  onToggleChecklistItem={() => {}}
                  onUpdateVendorStatus={() => {}}
                  onUpdateVendorNotes={() => {}}
                />
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Plan Rescue Modal */}
      <PlanRescueModal
        isOpen={isPlanRescueOpen}
        onClose={() => setIsPlanRescueOpen(false)}
        currentPlan={activePlan}
        onApplyPlan={(updated) => {
          updatePlan(updated, true, true, `Applied Plan Rescue! Now at Rev #${updated.metadata.revision}`);
        }}
      />
    </div>
  );
}
