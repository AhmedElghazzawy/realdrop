import { getDictionary, getLocale } from "@/i18n";
import { formatDay } from "@/lib/format";

// The real-drop rule (Phase 4) needs 14+ days of history before it may claim anything. Until then
// every product honestly shows the "insufficient_history" state (DESIGN_SYSTEM.md badge table).
export async function TrackingBadge({ since }: { since: string }) {
  const [locale, t] = [await getLocale(), await getDictionary()];
  return (
    <span className="inline-flex items-center gap-1 rounded border border-dashed border-line px-1.5 py-0.5 text-[11px] text-muted">
      <span aria-hidden>◷</span> {t.tracking(formatDay(locale, since))}
    </span>
  );
}
