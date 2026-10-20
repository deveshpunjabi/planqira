"use client";

import React from "react";
import { Sparkles, Palette, Music, Clock, Lightbulb, Check } from "lucide-react";
import { ThemeIdea } from "@/lib/schema";

interface IdeasTabProps {
  themes: ThemeIdea[];
  selectedThemeId: string;
  onSelectTheme: (themeId: string) => void;
}

export function IdeasTab({
  themes,
  selectedThemeId,
  onSelectTheme,
}: IdeasTabProps) {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-[#EADBDE]">
        <div>
          <h2 className="text-lg font-bold text-[#2B102B] flex items-center gap-2">
            <Palette className="w-5 h-5 text-[#D97706]" />
            Personalized Themes & Creative Concepts
          </h2>
          <p className="text-xs text-gray-600">
            3 curated bespoke event aesthetics with visual color swatches, sensory hooks, and affordable DIY alternatives.
          </p>
        </div>
        <span className="text-xs font-semibold text-[#7A397A] bg-[#F9F3FA] px-3 py-1 rounded-full border border-[#D8BFD8]">
          Select active theme
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {themes.map((theme) => {
          const isSelected = theme.id === selectedThemeId;

          return (
            <div
              key={theme.id}
              onClick={() => onSelectTheme(theme.id)}
              className={`relative rounded-2xl p-5 border transition-all cursor-pointer flex flex-col justify-between ${
                isSelected
                  ? "bg-white border-[#D97706] shadow-md ring-2 ring-[#D97706]/30"
                  : "bg-white/90 border-[#EADBDE] hover:border-[#D8BFD8] hover:shadow-sm"
              }`}
            >
              {/* Selected badge */}
              {isSelected && (
                <div className="absolute top-4 right-4 bg-[#D97706] text-white p-1 rounded-full shadow-sm">
                  <Check className="w-3.5 h-3.5" />
                </div>
              )}

              <div className="space-y-3.5">
                <div>
                  <h3 className="font-bold text-[#2B102B] text-base leading-snug">
                    {theme.name}
                  </h3>
                  <p className="text-xs text-[#7A397A] font-medium mt-0.5">
                    {theme.tagline}
                  </p>
                </div>

                {/* Color Swatch Circles */}
                <div className="bg-[#FAF7F2] p-2.5 rounded-xl border border-[#EADBDE]">
                  <div className="text-[10px] uppercase font-bold text-gray-500 mb-1.5 flex items-center justify-between">
                    <span>Palette Swatches</span>
                    <span className="font-mono text-[9px] text-gray-400">4-HEX</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {theme.paletteHex.map((hex, idx) => (
                      <div key={idx} className="flex-1 flex flex-col items-center gap-1 group">
                        <div
                          className="w-full h-7 rounded-lg shadow-inner border border-black/10 transition-transform group-hover:scale-105"
                          style={{ backgroundColor: hex }}
                          title={hex}
                        />
                        <span className="text-[9px] font-mono text-gray-600 truncate">
                          {hex}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Aesthetic Vibe */}
                <div className="text-xs text-gray-700">
                  <span className="font-semibold text-[#2B102B]">Aesthetic: </span>
                  {theme.aestheticVibe}
                </div>

                {/* Decor & Menu */}
                <div className="space-y-2 pt-1 border-t border-gray-100 text-xs">
                  <div>
                    <span className="font-semibold text-gray-900 block text-[11px] uppercase tracking-wider text-gray-500">
                      Decor Direction
                    </span>
                    <p className="text-gray-700 mt-0.5">{theme.decorDirection}</p>
                  </div>

                  <div>
                    <span className="font-semibold text-gray-900 block text-[11px] uppercase tracking-wider text-gray-500">
                      Culinary Direction
                    </span>
                    <p className="text-gray-700 mt-0.5">{theme.menuDirection}</p>
                  </div>
                </div>

                {/* Sensory Hook */}
                <div className="bg-purple-50/60 p-2.5 rounded-xl border border-purple-100 text-xs text-purple-950 flex items-start gap-2">
                  <Music className="w-4 h-4 text-purple-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <div className="font-semibold text-purple-900 text-[11px]">
                      Sensory Atmosphere
                    </div>
                    <div className="text-purple-900/90 mt-0.5">{theme.sensoryHook}</div>
                  </div>
                </div>

                {/* Signature Moment */}
                <div className="bg-amber-50/70 p-2.5 rounded-xl border border-amber-200 text-xs text-amber-950 flex items-start gap-2">
                  <Sparkles className="w-4 h-4 text-[#D97706] mt-0.5 flex-shrink-0" />
                  <div>
                    <div className="font-semibold text-amber-900 text-[11px]">
                      15-Minute Signature Moment
                    </div>
                    <div className="text-amber-900/90 mt-0.5">{theme.signatureMoment}</div>
                  </div>
                </div>
              </div>

              {/* DIY Budget Swap */}
              <div className="mt-4 pt-3 border-t border-gray-100 bg-[#FCFAF6] -mx-5 -mb-5 p-4 rounded-b-2xl border-t border-[#EADBDE]">
                <div className="flex items-start gap-2 text-xs text-emerald-950">
                  <Lightbulb className="w-4 h-4 text-emerald-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <span className="font-bold text-emerald-900 text-[11px] uppercase tracking-wide">
                      Low-Cost DIY Swap
                    </span>
                    <p className="text-emerald-900/80 mt-0.5 text-[11px] leading-relaxed">
                      {theme.diySwap}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
