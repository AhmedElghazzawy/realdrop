import { formatDay } from "@/lib/format";

// The real-drop rule (Phase 4) needs 14+ days of history before it may claim anything. Until then
// every product honestly shows the "insufficient_history" state (DESIGN_SYSTEM.md badge table).
export function TrackingBadge({ since }: { since: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded border border-dashed border-line px-1.5 py-0.5 text-[11px] text-muted">
      {/* No "'den/'dan beri" suffix: Turkish vowel harmony changes it with every date. */}
      <span aria-hidden>◷</span> Takip başlangıcı: {formatDay(since)}
    </span>
  );
}
