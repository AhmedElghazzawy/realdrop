"use client";

import Form from "next/form";

// A GET form that applies itself when a checkbox, radio or select changes, so filters and sort
// work like a shop's (text and number fields still wait for Enter or the Apply button). Without
// JavaScript it is a normal form with a submit button.
export function AutoSubmitForm({
  action,
  className,
  children,
}: {
  action: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <Form
      action={action}
      className={className}
      onChange={(event) => {
        const target = event.target;
        const toggled = target instanceof HTMLInputElement && (target.type === "checkbox" || target.type === "radio");
        if (toggled || target instanceof HTMLSelectElement) {
          event.currentTarget.requestSubmit();
        }
      }}
    >
      {children}
    </Form>
  );
}
