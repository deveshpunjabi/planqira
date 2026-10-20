"use client";

import React, { useRef } from "react";
import {
  Sparkles,
  Download,
  Upload,
  Printer,
  RotateCcw,
  CheckCircle2,
  AlertCircle,
  FileText,
} from "lucide-react";
import { EventPlan, PlanSource } from "@/lib/schema";

interface HeaderProps {
  plan: EventPlan;
  onImportPlan: (jsonString: string) => void;
  onExportPlan: () => void;
  onPrintPlan: () => void;
  onUndo: () => void;
  canUndo: boolean;
  saveMessage?: string;
}

export function Header({
  plan,
  onImportPlan,
  onExportPlan,
  onPrintPlan,
  onUndo,
  canUndo,
  saveMessage = "Saved locally",
}: HeaderProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      if (content) {
        onImportPlan(content);
      }
    };
    reader.readAsText(file);
    // Reset file input
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const getSourceBadge = (source: PlanSource) => {
    if (source === "live-ai") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200">
          <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
          Live AI Plan
        </span>
      );
    }
    if (source === "locally-edited") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-full bg-indigo-100 text-indigo-800 border border-indigo-200">
          <FileText className="w-3.5 h-3.5 text-indigo-600" />
          Locally Edited
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-full bg-amber-100 text-amber-900 border border-amber-300">
        <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
        Sample Plan • stored in this browser
      </span>
    );
  };

  return (
    <header className="sticky top-0 z-40 bg-[#FCFAF6]/95 backdrop-blur-md border-b border-[#EADBDE] px-4 py-3 sm:px-6 transition-all no-print">
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3">
        {/* Brand and Metadata */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#2D112C] to-[#5D295D] flex items-center justify-center text-white font-black shadow-sm text-lg">
            U
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-lg sm:text-xl font-bold tracking-tight text-[#2B102B]">
                UtsavAI
              </h1>
              <span className="text-xs uppercase tracking-widest text-[#7A397A] font-semibold hidden sm:inline">
                Celebration OS
              </span>
              {getSourceBadge(plan.metadata.source)}
              <span className="text-xs text-gray-500 font-mono">
                Rev #{plan.metadata.revision}
              </span>
            </div>
            <p className="text-xs text-gray-600 truncate max-w-xs sm:max-w-md">
              {plan.brief.title} • {plan.brief.city}
            </p>
          </div>
        </div>

        {/* Global Action Deck */}
        <div className="flex items-center gap-2 flex-wrap ml-auto">
          {/* Save Status */}
          <div className="hidden lg:flex items-center gap-1 text-xs text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-md border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{saveMessage}</span>
          </div>

          {/* Undo */}
          {canUndo && (
            <button
              onClick={onUndo}
              className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg text-gray-700 bg-white hover:bg-gray-100 border border-gray-200 transition-colors shadow-sm"
              title="Undo previous plan modification"
            >
              <RotateCcw className="w-3.5 h-3.5 text-[#D97706]" />
              <span>Undo</span>
            </button>
          )}

          {/* Hidden File Input for Import */}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".json,application/json"
            className="hidden"
          />

          {/* Import JSON */}
          <button
            onClick={() => fileInputRef.current?.click()}
            className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg text-gray-700 bg-white hover:bg-gray-100 border border-gray-200 transition-colors shadow-sm"
            title="Import an existing event JSON blueprint"
          >
            <Upload className="w-3.5 h-3.5 text-gray-500" />
            <span className="hidden sm:inline">Import</span>
          </button>

          {/* Export JSON */}
          <button
            onClick={onExportPlan}
            className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg text-gray-700 bg-white hover:bg-gray-100 border border-gray-200 transition-colors shadow-sm"
            title="Download full JSON blueprint backup"
          >
            <Download className="w-3.5 h-3.5 text-gray-500" />
            <span className="hidden sm:inline">Export JSON</span>
          </button>

          {/* Print / Save PDF */}
          <button
            onClick={onPrintPlan}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold rounded-lg text-white bg-[#2B102B] hover:bg-[#441D44] transition-colors shadow-sm"
            title="Print all 4 pillars or save as PDF"
          >
            <Printer className="w-3.5 h-3.5 text-[#F59E0B]" />
            <span>Print Plan</span>
          </button>
        </div>
      </div>
    </header>
  );
}
