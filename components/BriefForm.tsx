"use client";

import React, { useState } from "react";
import {
  Sparkles,
  Calendar,
  Users,
  Coins,
  MapPin,
  Clock,
  Compass,
  Info,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { CurrencyCode, EventBrief, EventType, SettingType } from "@/lib/schema";

interface BriefFormProps {
  brief: EventBrief;
  onUpdateBrief: (brief: EventBrief) => void;
  onGeneratePlan: (brief: EventBrief) => void;
  onSelectPreset: (presetKey: string) => void;
  isGenerating: boolean;
}

const COMMON_TIMEZONES = [
  "Asia/Kolkata",
  "America/New_York",
  "America/Los_Angeles",
  "Europe/London",
  "Europe/Paris",
  "Asia/Dubai",
  "Asia/Singapore",
  "UTC",
];

export function BriefForm({
  brief,
  onUpdateBrief,
  onGeneratePlan,
  onSelectPreset,
  isGenerating,
}: BriefFormProps) {
  const [showAssumptions, setShowAssumptions] = useState(false);
  const [formData, setFormData] = useState<EventBrief>(brief);

  // Keep local form in sync when brief prop changes (e.g. preset clicked)
  React.useEffect(() => {
    setFormData(brief);
  }, [brief]);

  const handleChange = (
    field: keyof EventBrief,
    value: string | number | SettingType | CurrencyCode | EventType
  ) => {
    const updated = { ...formData, [field]: value };
    setFormData(updated);
    onUpdateBrief(updated);
  };

  const handleBudgetChange = (majorAmount: number) => {
    const minor = Math.max(0, Math.round(majorAmount * 100));
    handleChange("totalBudget", minor);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onGeneratePlan(formData);
  };

  return (
    <div className="bg-white rounded-2xl border border-[#EADBDE] p-5 shadow-sm space-y-5">
      {/* Header and Presets */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-base font-bold text-[#2B102B] flex items-center gap-2">
            <Compass className="w-4 h-4 text-[#D97706]" />
            Event Brief & Constraints
          </h2>
          <span className="text-xs text-gray-500 font-medium">Step 1</span>
        </div>
        <p className="text-xs text-gray-600 mb-3">
          Select a verified judge preset to populate instant data, or customize your own celebration parameters.
        </p>

        {/* 4 One-Click Judge Presets */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-4">
          <button
            type="button"
            onClick={() => onSelectPreset("wedding")}
            className="text-left p-2.5 rounded-xl border border-amber-200 bg-amber-50/70 hover:bg-amber-100/70 transition-all text-xs group"
          >
            <div className="font-bold text-amber-950 flex items-center justify-between">
              <span>👑 Royal Heritage Wedding</span>
              <span className="text-[10px] text-amber-800 bg-amber-200/60 px-1.5 py-0.5 rounded font-mono">
                ₹12,00,000
              </span>
            </div>
            <div className="text-[11px] text-amber-800/80 mt-0.5 truncate">
              250 Guests • Jaipur • Pure Veg + Jain
            </div>
          </button>

          <button
            type="button"
            onClick={() => onSelectPreset("birthday")}
            className="text-left p-2.5 rounded-xl border border-purple-200 bg-purple-50/70 hover:bg-purple-100/70 transition-all text-xs group"
          >
            <div className="font-bold text-purple-950 flex items-center justify-between">
              <span>⚡ Neon Cyber 21st Birthday</span>
              <span className="text-[10px] text-purple-800 bg-purple-200/60 px-1.5 py-0.5 rounded font-mono">
                ₹35,000
              </span>
            </div>
            <div className="text-[11px] text-purple-800/80 mt-0.5 truncate">
              45 Guests • Bengaluru • Rooftop Vibes
            </div>
          </button>

          <button
            type="button"
            onClick={() => onSelectPreset("community")}
            className="text-left p-2.5 rounded-xl border border-emerald-200 bg-emerald-50/70 hover:bg-emerald-100/70 transition-all text-xs group"
          >
            <div className="font-bold text-emerald-950 flex items-center justify-between">
              <span>🌱 Neighborhood Eco-Fest</span>
              <span className="text-[10px] text-emerald-800 bg-emerald-200/60 px-1.5 py-0.5 rounded font-mono">
                ₹1,50,000
              </span>
            </div>
            <div className="text-[11px] text-emerald-800/80 mt-0.5 truncate">
              300 Guests • Pune • Zero-Waste Street Food
            </div>
          </button>

          <button
            type="button"
            onClick={() => onSelectPreset("gala")}
            className="text-left p-2.5 rounded-xl border border-blue-200 bg-blue-50/70 hover:bg-blue-100/70 transition-all text-xs group"
          >
            <div className="font-bold text-blue-950 flex items-center justify-between">
              <span>🎷 Golden 50th Birthday Gala</span>
              <span className="text-[10px] text-blue-800 bg-blue-200/60 px-1.5 py-0.5 rounded font-mono">
                $5,000
              </span>
            </div>
            <div className="text-[11px] text-blue-800/80 mt-0.5 truncate">
              75 Guests • Boston • Live Jazz Pavilion
            </div>
          </button>
        </div>
      </div>

      {/* Main Interactive Form */}
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Event Type & Setting */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Event Category
            </label>
            <select
              value={formData.eventType}
              onChange={(e) => handleChange("eventType", e.target.value as EventType)}
              className="w-full text-xs font-medium rounded-lg border border-gray-300 bg-white px-2.5 py-2 text-gray-900 focus:border-[#D97706] focus:ring-1 focus:ring-[#D97706]"
            >
              <option value="wedding">Wedding Celebration</option>
              <option value="birthday">Birthday Party</option>
              <option value="community">Community & Public Event</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Venue Setting
            </label>
            <select
              value={formData.setting}
              onChange={(e) => handleChange("setting", e.target.value as SettingType)}
              className="w-full text-xs font-medium rounded-lg border border-gray-300 bg-white px-2.5 py-2 text-gray-900 focus:border-[#D97706] focus:ring-1 focus:ring-[#D97706]"
            >
              <option value="indoor">Indoor (Protected)</option>
              <option value="outdoor">Outdoor (Weather Dependent)</option>
              <option value="hybrid">Hybrid (Indoor + Lawn)</option>
            </select>
          </div>
        </div>

        {/* Title */}
        <div>
          <label className="block text-xs font-semibold text-gray-700 mb-1">
            Celebration Title
          </label>
          <input
            type="text"
            value={formData.title}
            onChange={(e) => handleChange("title", e.target.value)}
            className="w-full text-xs rounded-lg border border-gray-300 px-3 py-2 text-gray-900 focus:border-[#D97706] focus:ring-1 focus:ring-[#D97706]"
            required
            maxLength={120}
          />
        </div>

        {/* Budget and Currency */}
        <div className="grid grid-cols-3 gap-2">
          <div className="col-span-2">
            <label className="block text-xs font-semibold text-gray-700 mb-1 flex items-center gap-1">
              <Coins className="w-3.5 h-3.5 text-[#D97706]" />
              Total Budget
            </label>
            <input
              type="number"
              min={100}
              value={Math.round(formData.totalBudget / 100)}
              onChange={(e) => handleBudgetChange(Number(e.target.value))}
              className="w-full text-xs font-semibold rounded-lg border border-gray-300 px-3 py-2 text-gray-900 focus:border-[#D97706] focus:ring-1 focus:ring-[#D97706]"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Currency
            </label>
            <select
              value={formData.currency}
              onChange={(e) => handleChange("currency", e.target.value as CurrencyCode)}
              className="w-full text-xs font-medium rounded-lg border border-gray-300 bg-white px-2 py-2 text-gray-900 focus:border-[#D97706] focus:ring-1 focus:ring-[#D97706]"
            >
              <option value="INR">INR (₹)</option>
              <option value="USD">USD ($)</option>
              <option value="EUR">EUR (€)</option>
            </select>
          </div>
        </div>

        {/* Guests, Date, and Time */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1 flex items-center gap-1">
              <Users className="w-3.5 h-3.5 text-gray-500" />
              Guests
            </label>
            <input
              type="number"
              min={1}
              max={10000}
              value={formData.guestCount}
              onChange={(e) => handleChange("guestCount", Math.max(1, parseInt(e.target.value) || 1))}
              className="w-full text-xs rounded-lg border border-gray-300 px-2.5 py-2 text-gray-900 focus:border-[#D97706] focus:ring-1 focus:ring-[#D97706]"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1 flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5 text-gray-500" />
              Event Date
            </label>
            <input
              type="date"
              value={formData.eventDate}
              onChange={(e) => handleChange("eventDate", e.target.value)}
              className="w-full text-xs rounded-lg border border-gray-300 px-2 py-2 text-gray-900 focus:border-[#D97706] focus:ring-1 focus:ring-[#D97706]"
              required
            />
          </div>

          <div className="col-span-2 sm:col-span-1">
            <label className="block text-xs font-semibold text-gray-700 mb-1 flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-gray-500" />
              Start Time
            </label>
            <input
              type="time"
              value={formData.startTime}
              onChange={(e) => handleChange("startTime", e.target.value)}
              className="w-full text-xs rounded-lg border border-gray-300 px-2 py-2 text-gray-900 focus:border-[#D97706] focus:ring-1 focus:ring-[#D97706]"
              required
            />
          </div>
        </div>

        {/* City & Timezone */}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1 flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5 text-gray-500" />
              City / Region
            </label>
            <input
              type="text"
              value={formData.city}
              onChange={(e) => handleChange("city", e.target.value)}
              placeholder="e.g. Mumbai, Jaipur, Austin"
              className="w-full text-xs rounded-lg border border-gray-300 px-2.5 py-2 text-gray-900 focus:border-[#D97706] focus:ring-1 focus:ring-[#D97706]"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Timezone
            </label>
            <select
              value={formData.timezone}
              onChange={(e) => handleChange("timezone", e.target.value)}
              className="w-full text-xs rounded-lg border border-gray-300 bg-white px-2 py-2 text-gray-900 focus:border-[#D97706] focus:ring-1 focus:ring-[#D97706]"
            >
              {COMMON_TIMEZONES.map((tz) => (
                <option key={tz} value={tz}>
                  {tz}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Cultural & Dietary Customizations */}
        <div>
          <label className="block text-xs font-semibold text-gray-700 mb-1">
            Dietary & Catering Specifics
          </label>
          <input
            type="text"
            value={formData.dietaryRestrictions}
            onChange={(e) => handleChange("dietaryRestrictions", e.target.value)}
            placeholder="e.g. Pure Veg + Jain counter, Halal, Nut-free, Gluten-free"
            className="w-full text-xs rounded-lg border border-gray-300 px-3 py-2 text-gray-900 focus:border-[#D97706] focus:ring-1 focus:ring-[#D97706]"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-700 mb-1">
            Cultural & Vibe Preferences
          </label>
          <input
            type="text"
            value={formData.culturalPreferences}
            onChange={(e) => handleChange("culturalPreferences", e.target.value)}
            placeholder="e.g. Vedic rituals without alcohol, 90s retro games, quiet zones"
            className="w-full text-xs rounded-lg border border-gray-300 px-3 py-2 text-gray-900 focus:border-[#D97706] focus:ring-1 focus:ring-[#D97706]"
          />
        </div>

        {/* Disclosed Assumptions Card */}
        {formData.assumptions && formData.assumptions.length > 0 && (
          <div className="border border-amber-200 bg-amber-50/50 rounded-xl p-3">
            <button
              type="button"
              onClick={() => setShowAssumptions(!showAssumptions)}
              className="w-full flex items-center justify-between text-xs font-semibold text-amber-900"
            >
              <span className="flex items-center gap-1.5">
                <Info className="w-3.5 h-3.5 text-amber-600" />
                Disclosed Smart Assumptions ({formData.assumptions.length})
              </span>
              {showAssumptions ? (
                <ChevronUp className="w-3.5 h-3.5" />
              ) : (
                <ChevronDown className="w-3.5 h-3.5" />
              )}
            </button>

            {showAssumptions && (
              <div className="mt-2.5 space-y-2 border-t border-amber-200 pt-2 text-[11px] text-amber-950">
                {formData.assumptions.map((item, idx) => (
                  <div key={idx} className="bg-white/80 p-2 rounded-lg border border-amber-100">
                    <div className="font-semibold text-amber-900">{item.field}:</div>
                    <div className="text-gray-700">{item.assumption}</div>
                    <div className="text-gray-500 italic mt-0.5 text-[10px]">
                      Reason: {item.editableReason}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Action Button */}
        <button
          type="submit"
          disabled={isGenerating}
          className="w-full py-2.5 px-4 rounded-xl text-white text-xs sm:text-sm font-bold bg-gradient-to-r from-[#2B102B] via-[#441D44] to-[#5D295D] hover:opacity-95 transition-all shadow-md flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isGenerating ? (
            <>
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>Generating Plan via Gemini...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4 text-[#F59E0B]" />
              <span>Architect Event Blueprint</span>
            </>
          )}
        </button>
      </form>
    </div>
  );
}
