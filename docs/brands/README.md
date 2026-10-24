# Brand feasibility

One file per candidate brand (`<slug>.md`), written during the feasibility step of the
add-brand-collector skill. The owner makes the go / no-go call and records it in the file.

Checked 24 Oct 2026 with our own User-Agent (`RealDropBot/0.1`), a handful of requests per site,
2 s apart.

| Brand | robots.txt | Terms | Data | Per-size stock | Recommendation |
|---|---|---|---|---|---|
| [DeFacto](defacto.md) | Product pages allowed | No public terms page found | JSON-LD + embedded JSON | Yes, in page | **Go: brand 1** |
| [Colin's](colins.md) | Product pages allowed (`*price*` URLs disallowed) | No anti-bot clause found | JSON-LD + HTML | Sizes yes, stock unclear | Go: brand 2 (after a stock check) |
| [Koton](koton.md) | Product pages allowed | Not verified (page renders client-side) | JSON-LD (one size) | Needs an XHR endpoint | Maybe: brand 3 (needs DevTools look) |
| [LC Waikiki](lc-waikiki.md) | Allows everything | **Forbids robots, crawling, data mining** | JSON-LD | Not in page | No-go |
| [Mavi](mavi.md) | Product pages allowed | Not checked | Not reached | Not reached | No-go (Cloudflare challenge) |
| [H&M Turkey](hm-turkey.md) | **403 on robots.txt** | Not checked | Not reached | Not reached | No-go (blocked) |
