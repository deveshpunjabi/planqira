"use client";

import React, { useState } from "react";
import {
  Calendar,
  CheckCircle2,
  Clock,
  AlertCircle,
  CheckSquare,
  Square,
  HelpCircle,
  Eye,
  Wrench,
} from "lucide-react";
import { DayOfBlock, PreparationTask } from "@/lib/schema";

interface TimelineTabProps {
  preparationTasks: PreparationTask[];
  dayOfRunOfShow: DayOfBlock[];
  onToggleTaskCompletion: (taskId: string) => void;
  eventDate: string;
}

export function TimelineTab({
  preparationTasks,
  dayOfRunOfShow,
  onToggleTaskCompletion,
  eventDate,
}: TimelineTabProps) {
  const [activeSubTab, setActiveSubTab] = useState<"countdown" | "runofshow">("countdown");
  const [showFormulaTooltip, setShowFormulaTooltip] = useState(false);

  const completedCount = preparationTasks.filter((t) => t.isCompleted).length;
  const totalCount = preparationTasks.length;
  const readinessPercent = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  const getPriorityBadge = (priority: "critical" | "high" | "medium") => {
    if (priority === "critical") {
      return (
        <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-red-100 text-red-800 border border-red-200">
          Critical
        </span>
      );
    }
    if (priority === "high") {
      return (
        <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-200">
          High
        </span>
      );
    }
    return (
      <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-blue-100 text-blue-800 border border-blue-200">
        Medium
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header and View Toggle */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-[#EADBDE]">
        <div>
          <h2 className="text-lg font-bold text-[#2B102B] flex items-center gap-2">
            <Calendar className="w-5 h-5 text-[#D97706]" />
            Dual-Layer Timeline & Run-of-Show
          </h2>
          <p className="text-xs text-gray-600">
            Date-compressed preparation countdown paired with day-of Front-of-House vs. Back-of-House choreography.
          </p>
        </div>

        {/* Sub-tab toggle */}
        <div className="flex bg-[#F8F4EC] p-1 rounded-xl border border-[#EADBDE] self-start sm:self-auto">
          <button
            type="button"
            onClick={() => setActiveSubTab("countdown")}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              activeSubTab === "countdown"
                ? "bg-white text-[#2B102B] shadow-sm"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            T-Minus Countdown ({preparationTasks.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveSubTab("runofshow")}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              activeSubTab === "runofshow"
                ? "bg-white text-[#2B102B] shadow-sm"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            Day-Of Run-of-Show ({dayOfRunOfShow.length})
          </button>
        </div>
      </div>

      {activeSubTab === "countdown" ? (
        <div className="space-y-4">
          {/* Planning Readiness Score Meter */}
          <div className="bg-white rounded-2xl p-4 border border-[#EADBDE] shadow-sm space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-xs font-bold text-[#2B102B]">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>Planning Readiness Metric</span>
                <button
                  type="button"
                  onClick={() => setShowFormulaTooltip(!showFormulaTooltip)}
                  className="text-gray-400 hover:text-gray-600"
                  title="View calculation formula"
                >
                  <HelpCircle className="w-3.5 h-3.5" />
                </button>
              </div>
              <div className="text-sm font-black text-[#2B102B] font-mono">
                {readinessPercent}% Ready ({completedCount}/{totalCount} Completed)
              </div>
            </div>

            {/* Formula disclosure */}
            {showFormulaTooltip && (
              <div className="p-2.5 rounded-lg bg-[#FAF7F2] text-[11px] text-gray-700 border border-[#EADBDE]">
                <span className="font-semibold text-gray-900">Formula: </span>
                <code className="font-mono bg-white px-1.5 py-0.5 rounded border border-gray-200">
                  (completed applicable milestones / total applicable milestones) * 100
                </code>
                <p className="mt-1 text-gray-500">
                  Note: This measures checklist milestone execution, not guaranteed event outcome probability.
                </p>
              </div>
            )}

            {/* Progress Bar */}
            <div className="w-full bg-gray-100 h-3 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-[#D97706] to-[#059669] transition-all duration-300"
                style={{ width: `${readinessPercent}%` }}
              />
            </div>
          </div>

          {/* Checklist Milestone Cards */}
          <div className="space-y-2.5">
            {preparationTasks.map((task) => (
              <div
                key={task.id}
                onClick={() => onToggleTaskCompletion(task.id)}
                className={`p-3.5 rounded-2xl border transition-all cursor-pointer flex items-start gap-3 ${
                  task.isCompleted
                    ? "bg-emerald-50/40 border-emerald-200 text-gray-500"
                    : "bg-white border-[#EADBDE] hover:border-gray-300 text-gray-900 shadow-sm"
                }`}
              >
                <button
                  type="button"
                  className="mt-0.5 text-gray-400 hover:text-emerald-600 flex-shrink-0"
                >
                  {task.isCompleted ? (
                    <CheckSquare className="w-5 h-5 text-emerald-600" />
                  ) : (
                    <Square className="w-5 h-5 text-gray-400" />
                  )}
                </button>

                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-mono font-bold bg-[#F8F4EC] px-2 py-0.5 rounded text-[#2B102B]">
                      {task.timeframe}
                    </span>
                    <span className={`text-xs font-bold ${task.isCompleted ? "line-through text-gray-400" : "text-[#2B102B]"}`}>
                      {task.title}
                    </span>
                    {getPriorityBadge(task.priority)}
                    {task.isOverdue && !task.isCompleted && (
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-100 text-red-800 border border-red-200 flex items-center gap-1">
                        <AlertCircle className="w-3 h-3 text-red-600" /> Overdue
                      </span>
                    )}
                  </div>

                  <p className="text-xs text-gray-600 mt-1">
                    {task.description}
                  </p>

                  <div className="flex items-center gap-4 mt-2 text-[11px] text-gray-500">
                    <div>
                      <span className="font-medium text-gray-700">Due: </span>
                      <span className="font-mono">{task.dueDate}</span>
                    </div>
                    <div>
                      <span className="font-medium text-gray-700">Owner: </span>
                      <span>{task.owner}</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        /* Day-Of Run of Show (Front-of-House vs Back-of-House) */
        <div className="space-y-4">
          <div className="bg-amber-50/60 p-3 rounded-xl border border-amber-200 text-xs text-amber-950 flex items-center gap-2">
            <Clock className="w-4 h-4 text-[#D97706] flex-shrink-0" />
            <span>
              Targeted event schedule for <strong>{eventDate}</strong> with strict choreography between guest perception and crew operations.
            </span>
          </div>

          <div className="space-y-3">
            {dayOfRunOfShow.map((block) => (
              <div
                key={block.id}
                className="bg-white rounded-2xl border border-[#EADBDE] p-4 shadow-sm"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-gray-100">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-black bg-[#2D112C] text-white px-2.5 py-1 rounded-lg">
                      {block.timeSlot}
                    </span>
                  </div>
                  <span className="text-xs font-semibold text-gray-600 bg-gray-100 px-2.5 py-0.5 rounded-full">
                    Lead: {block.leadVendorOrRole}
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
                  {/* Front-of-House */}
                  <div className="p-3 rounded-xl bg-purple-50/50 border border-purple-100">
                    <div className="flex items-center gap-1.5 text-xs font-bold text-purple-900 mb-1">
                      <Eye className="w-3.5 h-3.5 text-purple-600" />
                      <span>Front-of-House (Guest Perception)</span>
                    </div>
                    <p className="text-xs text-purple-950 leading-relaxed">
                      {block.frontOfHouseGuestView}
                    </p>
                  </div>

                  {/* Back-of-House */}
                  <div className="p-3 rounded-xl bg-amber-50/50 border border-amber-100">
                    <div className="flex items-center gap-1.5 text-xs font-bold text-amber-900 mb-1">
                      <Wrench className="w-3.5 h-3.5 text-[#D97706]" />
                      <span>Back-of-House (Vendor & Crew Action)</span>
                    </div>
                    <p className="text-xs text-amber-950 leading-relaxed">
                      {block.backOfHouseCrewAction}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
