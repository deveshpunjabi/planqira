"use client";

import React, { useState } from "react";
import {
  Briefcase,
  AlertOctagon,
  Copy,
  Check,
  CheckSquare,
  Square,
  FileSignature,
  DollarSign,
} from "lucide-react";
import { VendorRecord } from "@/lib/schema";

interface VendorsTabProps {
  vendors: VendorRecord[];
  onToggleChecklistItem: (vendorId: string, itemId: string) => void;
  onUpdateVendorStatus: (
    vendorId: string,
    status: "not-started" | "inquiry-sent" | "quote-received" | "booked"
  ) => void;
  onUpdateVendorNotes: (vendorId: string, notes: string) => void;
}

export function VendorsTab({
  vendors,
  onToggleChecklistItem,
  onUpdateVendorStatus,
  onUpdateVendorNotes,
}: VendorsTabProps) {
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleCopyScript = (vendorId: string, scriptText: string) => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(scriptText).then(() => {
        setCopiedId(vendorId);
        setTimeout(() => setCopiedId(null), 2500);
      });
    } else {
      // Fallback
      setCopiedId(vendorId);
      setTimeout(() => setCopiedId(null), 2500);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-[#EADBDE]">
        <div>
          <h2 className="text-lg font-bold text-[#2B102B] flex items-center gap-2">
            <Briefcase className="w-5 h-5 text-[#D97706]" />
            Vendor Interrogation Kit & Negotiation Protocols
          </h2>
          <p className="text-xs text-gray-600">
            Contract verification guardrails, hidden-fee trap questions, and 1-click negotiation scripts.
          </p>
        </div>
        <span className="text-xs text-gray-500 font-mono">
          {vendors.filter((v) => v.status === "booked").length} of {vendors.length} Booked
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {vendors.map((vendor) => {
          const isCopied = copiedId === vendor.id;

          return (
            <div
              key={vendor.id}
              className="bg-white rounded-2xl border border-[#EADBDE] p-5 shadow-sm space-y-4 hover:border-gray-300 transition-all"
            >
              {/* Card Header */}
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className="text-[10px] uppercase font-bold tracking-wider text-[#7A397A] bg-purple-50 px-2 py-0.5 rounded border border-purple-100">
                    {vendor.category}
                  </span>
                  <h3 className="font-bold text-[#2B102B] text-base mt-1">
                    {vendor.title}
                  </h3>
                  <div className="text-xs text-gray-500 mt-0.5">
                    Recommended Booking: <span className="font-semibold text-gray-700">{vendor.bookingWindow}</span>
                  </div>
                </div>

                {/* Booking Status Dropdown */}
                <select
                  value={vendor.status}
                  onChange={(e) =>
                    onUpdateVendorStatus(
                      vendor.id,
                      e.target.value as "not-started" | "inquiry-sent" | "quote-received" | "booked"
                    )
                  }
                  className={`text-xs font-semibold rounded-lg border px-2.5 py-1.5 transition-colors ${
                    vendor.status === "booked"
                      ? "bg-emerald-50 text-emerald-800 border-emerald-300 font-bold"
                      : vendor.status === "quote-received"
                      ? "bg-blue-50 text-blue-800 border-blue-200"
                      : vendor.status === "inquiry-sent"
                      ? "bg-amber-50 text-amber-800 border-amber-200"
                      : "bg-gray-50 text-gray-600 border-gray-200"
                  }`}
                >
                  <option value="not-started">⚪ Not Started</option>
                  <option value="inquiry-sent">🟡 Inquiry Sent</option>
                  <option value="quote-received">🔵 Quote Received</option>
                  <option value="booked">🟢 Confirmed / Booked</option>
                </select>
              </div>

              {/* Hidden Fee Trap Question Alert Box */}
              <div className="p-3 rounded-xl bg-amber-50/70 border border-amber-300 text-amber-950 text-xs flex items-start gap-2.5">
                <AlertOctagon className="w-4 h-4 text-[#D97706] flex-shrink-0 mt-0.5" />
                <div className="space-y-0.5">
                  <div className="font-bold text-amber-900 text-[11px] uppercase tracking-wide">
                    Hidden-Fee Trap Question (Ask Before Signing)
                  </div>
                  <div className="text-amber-900 font-medium italic">
                    &ldquo;{vendor.hiddenFeeTrapQuestion}&rdquo;
                  </div>
                </div>
              </div>

              {/* Contract Checklist Items */}
              <div>
                <div className="text-[11px] font-bold uppercase tracking-wider text-gray-500 mb-2 flex items-center gap-1">
                  <FileSignature className="w-3.5 h-3.5" />
                  <span>Must-Verify Contract Clauses</span>
                </div>
                <div className="space-y-1.5 bg-[#FAF7F2] p-2.5 rounded-xl border border-[#EADBDE]">
                  {vendor.contractChecklist.map((item) => (
                    <div
                      key={item.id}
                      onClick={() => onToggleChecklistItem(vendor.id, item.id)}
                      className="flex items-center gap-2 text-xs text-gray-700 cursor-pointer hover:text-gray-900 select-none py-0.5"
                    >
                      <button type="button" className="text-gray-400 hover:text-emerald-600">
                        {item.checked ? (
                          <CheckSquare className="w-4 h-4 text-emerald-600" />
                        ) : (
                          <Square className="w-4 h-4 text-gray-400" />
                        )}
                      </button>
                      <span className={item.checked ? "line-through text-gray-400" : ""}>
                        {item.item}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Ready-to-Send Negotiation Script */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-gray-500">
                    WhatsApp / Email Negotiation Draft
                  </span>
                  <button
                    type="button"
                    onClick={() => handleCopyScript(vendor.id, vendor.inquiryScript)}
                    className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#7A397A] hover:text-[#2B102B] bg-[#F9F3FA] px-2 py-0.5 rounded border border-[#D8BFD8] transition-colors"
                  >
                    {isCopied ? (
                      <>
                        <Check className="w-3 h-3 text-emerald-600" />
                        <span className="text-emerald-700">Copied to Clipboard!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" />
                        <span>Copy Script</span>
                      </>
                    )}
                  </button>
                </div>
                <textarea
                  readOnly
                  value={vendor.inquiryScript}
                  rows={3}
                  className="w-full text-[11px] font-mono text-gray-700 bg-gray-50/70 rounded-xl border border-gray-200 p-2.5 focus:outline-none resize-none"
                />
              </div>

              {/* User Notes */}
              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-gray-500 mb-1">
                  Private Negotiation Notes & Agreed Rates
                </label>
                <input
                  type="text"
                  value={vendor.notes}
                  onChange={(e) => onUpdateVendorNotes(vendor.id, e.target.value)}
                  placeholder="e.g. Offered ₹45,000 all-inclusive, waiting on revised menu draft"
                  className="w-full text-xs rounded-xl border border-gray-300 px-3 py-2 text-gray-900 focus:border-[#D97706] focus:ring-1 focus:ring-[#D97706]"
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
