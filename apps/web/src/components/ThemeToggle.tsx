"use client";

import { useSyncExternalStore } from "react";
import { MoonIcon, SunIcon } from "./icons";

type Theme = "light" | "dark";

// The page starts in the device's theme, or the one picked here before (localStorage, applied
// before paint by the script in layout.tsx). Picking one sets data-theme on <html>.
const DARK = "(prefers-color-scheme: dark)";

// The theme lives outside React (data-theme on <html> and the device setting), so it is read as
// an external store and re-read when either changes.
function subscribe(onChange: () => void) {
  const media = window.matchMedia(DARK);
  media.addEventListener("change", onChange);
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributeFilter: ["data-theme"] });
  return () => {
    media.removeEventListener("change", onChange);
    observer.disconnect();
  };
}

function current(): Theme {
  const chosen = document.documentElement.dataset.theme;
  if (chosen === "light" || chosen === "dark") return chosen;
  return window.matchMedia(DARK).matches ? "dark" : "light";
}

export function ThemeToggle({ labels }: { labels: { toLight: string; toDark: string } }) {
  const theme = useSyncExternalStore<Theme | null>(subscribe, current, () => null);

  function toggle() {
    const next: Theme = theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem("theme", next);
    } catch {
      // Private mode or blocked storage: the switch still works for this page view.
    }
  }

  const label = theme === "dark" ? labels.toLight : labels.toDark;
  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={label}
      title={label}
      className="grid size-10 place-items-center text-text hover:text-muted"
    >
      {/* Before hydration the theme is unknown; render a stable icon to avoid a mismatch. */}
      {theme === "dark" ? <SunIcon /> : <MoonIcon />}
    </button>
  );
}
