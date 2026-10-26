"use client";

import { usePathname, useSearchParams } from "next/navigation";
import { useEffect, useRef } from "react";
import { CloseIcon } from "./icons";

// A side sheet on <dialog> (focus trap, Esc closes, page inert). Children are server-rendered;
// it closes itself after any navigation (a link, or a filter form submitting).
export function Drawer({
  trigger,
  triggerClassName,
  label,
  closeLabel,
  side = "left",
  children,
}: {
  trigger: React.ReactNode;
  triggerClassName?: string;
  label: string;
  closeLabel: string;
  side?: "left" | "right";
  children: React.ReactNode;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const pathname = usePathname();
  const query = useSearchParams().toString();

  useEffect(() => {
    dialog.current?.close();
  }, [pathname, query]);

  return (
    <>
      <button
        type="button"
        onClick={() => dialog.current?.showModal()}
        aria-label={typeof trigger === "string" ? undefined : label}
        className={triggerClassName}
      >
        {trigger}
      </button>
      <dialog
        ref={dialog}
        aria-label={label}
        className={`m-0 h-dvh max-h-none w-[min(24rem,90vw)] max-w-none bg-bg p-0 text-text backdrop:bg-black/40 ${
          side === "right" ? "ml-auto" : ""
        }`}
        onClick={(event) => {
          if (event.target === dialog.current) dialog.current.close(); // a click on the backdrop
        }}
      >
        <div className="flex h-full flex-col">
          <div className="flex items-center justify-between border-b border-line py-2 pl-5 pr-2">
            <p className="text-sm font-medium">{label}</p>
            <button
              type="button"
              onClick={() => dialog.current?.close()}
              aria-label={closeLabel}
              className="grid size-10 place-items-center"
            >
              <CloseIcon />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto px-5 py-4">{children}</div>
        </div>
      </dialog>
    </>
  );
}
