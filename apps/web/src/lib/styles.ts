// Style tags the catalog tagger assigns (apps/api/src/realdrop/pipeline/tagger.py STYLES).
// Ordered for the home page: the styles people ask for most come first.

export const STYLES = [
  "old_money",
  "streetwear",
  "minimal",
  "smart_casual",
  "classic_tailoring",
  "sporty",
  "workwear",
  "preppy",
  "techwear",
  "y2k",
] as const;

export type StyleKey = (typeof STYLES)[number];

export function isStyle(value: string): value is StyleKey {
  return (STYLES as readonly string[]).includes(value);
}
