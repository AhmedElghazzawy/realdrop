"use client"; // Error boundaries must be Client Components

export default function ErrorPage({ retry }: { error: unknown; retry: () => void }) {
  return (
    <div className="rounded-card border border-warn/40 p-8 text-center">
      <p className="mb-1 font-serif text-2xl">Veriye ulaşamadık.</p>
      <p className="mb-4 text-sm text-muted">API çalışmıyor olabilir. Biraz sonra tekrar deneyin.</p>
      <button onClick={() => retry()} className="rounded-card bg-text px-4 py-2 text-sm text-bg">
        Tekrar dene
      </button>
    </div>
  );
}
