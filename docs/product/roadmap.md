# Roadmap: phases to Black Friday (Fri 27 Nov 2026)

Work goes by **phases, not days**. Start the next phase as soon as the current one is done; finishing
several in one day is fine. Update the checkboxes and the README progress table as work completes.

Each phase has a **latest finish** date. Being ahead is the goal; passing a latest-finish date with the
phase still open is the signal to apply the cut lines at the bottom. Do not silently slip.

**The one thing that cannot slip:** price collection must run on a **server** as early as possible,
**27 Oct at the latest** (end of Phase 3). History is the asset competitors cannot fake; every missing
day is lost forever, and the real-drop rule needs 14+ days of history before it can make any claim.

## Phase 1: environment ✅

Latest finish: 24 Oct.

- [x] Environment from `docs/engineering/setup.md` (tools, apps scaffolded, Postgres, Ollama), kit committed,
      repo on GitHub.
- [x] Switch to free and open-source models only (ADR 11).
- [ ] Owner reads `docs/product/vision.md`, `docs/product/use-cases.md`, `docs/architecture/overview.md` once.

## Phase 2: backend foundation ✅

Latest finish: 25 Oct. Done 24 Oct.

- [x] Settings, async DB session, app factory. `/health`. (`text.py` tests: done in Phase 1.)
- [x] Alembic setup + first migration (catalog, prices, runs).
- [x] Base collector interface, polite HTTP client, price parsing + fixture-test pattern.

## Phase 3: first brand collecting on a server

Latest finish: 27 Oct.

- [x] Feasibility check for the first 3 brands (`docs/data-sources/<slug>.md`: robots, terms, feed or JSON,
      stability). Pick the easiest. (Six checked; DeFacto is brand 1.)
- [x] Brand 1 collector against fixtures; dry run of 20 products.
- [x] Brand 1 stored in DB with validation (glitch filter).
- [x] Production database on Neon free + daily collection on GitHub Actions (`docs/operations/deployment.md`; no-card
      free tiers only, ADR 12). **Collection is now running without the laptop.** (Test runs from
      GitHub to Neon green 25 Oct; first scheduled full runs 25 Oct 03:00 and 15:00 Turkey time.)

## Phase 4: more brands and the real-drop rule

Latest finish: 31 Oct.

- [ ] Brands 2 and 3. `price_daily` roll-up, `current_prices`.
  - [x] Brand 2: Colin's (25 Oct). Change-only observations + `price_daily` roll-up (25 Oct, owner
        decision for storage). `current_prices` deferred: catalog queries are fast enough so far.
  - [x] Brands 3-7: Koton, Mudo, GAP, Marks & Spencer, Damat Tween through one Akinon collector
        (27 Oct; men's products only, owner 26 Oct). Wide brand scan: docs/data-sources/README.md.
  - [x] Brand 8: Les Benjamins through a Shopify collector (27 Oct). Giesto and Ramsey answer
        429 to our identified requests: retry later.
  - [x] Brands 9-11: Lufian, TommyLife, Hatemoğlu through a T-Soft collector (27 Oct).
- [ ] More platform groups (owner, 26 Oct: "all the big brands"): newer Akinon (U.S. Polo Assn.,
      Pierre Cardin); own-platform brands (Network, Altınyıldız, Yargıcı, Twist, Beymen, ...).
      Waiting on the owner: terms for Sarar, AVVA, Bad Bear, Loft. Süvari: no-go (terms).
- [ ] Collection health report (success rate per brand).
- [x] `pricing/real_drop.py` with the full test suite (pure functions).

Later (owner, 25 Oct): the UI style needs a design pass, and a men/women choice; not before the
data work above is done.

## The pivot (owner, 14 Nov 2026)

RealDrop becomes an **AI fashion advisor**: the user picks their style, shows outfits they like (a
screenshot from Instagram or Pinterest), and gets real products from every brand we track that make
that look, at real prices. Owner decisions:
- Keep the **27 Nov launch** with an MVP.
- Keep price honesty as a feature: every recommendation shows the real discount.
- Store the style profile **on the device first** (no login). Optional login to sync comes later.

Phases 5-11 below replace the old plan (extractor, hybrid search, query parser, web app, alerts,
assistant, personalization). The useful parts of the old plan are folded into the new phases.

## Phase 5: catalog understanding

Latest finish: 17 Nov.

- [ ] Fashion attribute schema: category, colour, pattern, material, fit, formality, season, and
      **style tags** (old money, streetwear, minimal, smart casual, classic tailoring, techwear,
      workwear, sporty, Y2K, preppy, ...). Turkish and English synonyms.
- [ ] Tag the catalog: rules from titles first, then the LLM extractor with local Ollama for the
      rest (dry-run time estimate first; overnight). Label 60 products by hand for an eval.
- [ ] bge-m3 text embeddings + pgvector; attribute-filtered semantic search API.
- [ ] Raise collection frequency to every 4 h for the run-up to the sale (17 Nov at the latest).

## Phase 6: style profile and "For you"

Latest finish: 19 Nov.

- [ ] Onboarding: pick styles from mood images, fits, colours liked or avoided, budget, sizes,
      favourite brands. Saved on the device; editable at any time.
- [ ] "For you" feed: bounded re-ranking by profile, with "because you like old money" labels.

## Phase 7: shop the look

Latest finish: 22 Nov.

- [ ] Photo upload (screenshot or picture). Free vision model (Gemini or Groq free tier, chosen by a
      small eval) finds each piece and describes it in the Phase 5 schema.
- [ ] Per piece: 3-5 matches across brands via the Phase 5 search, in the user's sizes and budget,
      with the real-discount flag. "Cheaper alternative" option.
- [ ] Photos are not stored; the privacy notice says which provider sees them.

## Phase 8: advisor redesign

Latest finish: 23 Nov.

- [ ] Home becomes the advisor: upload a look, ask the stylist, your feed. Shop and brands stay as
      secondary pages. Outfit boards (top, bottom, shoes, layer, accessory) with a total price.
- [ ] Modern look and mobile first; English + Turkish strings.

## Phase 9: AI stylist chat (Should)

Latest finish: 24 Nov.

- [ ] Tool loop over the catalog: "old money outfit for a wedding under 4,000 TL" returns outfit
      boards. "Complete the look" on every product page.
- [ ] Number-grounding guard (no price that did not come from a tool), prompt-injection tests.

## Phase 10: launch

Latest finish: 27 Nov. The last three steps are tied to fixed dates.

- [ ] Black Friday page (real best deals, inflated-claim examples). KVKK pages: privacy notice
      (including uploaded photos), consent, delete-my-data.
- [ ] Error pages, Sentry, rate limits on the AI endpoints (free-tier quotas), backups verified.
- [ ] Eval run; fix the worst failures; **freeze features (25 Nov)**.
- [ ] **Soft launch to friends (26 Nov)**; watch logs, free-tier rate limits.
- [ ] **Black Friday (27 Nov).** Monitor collection every few hours. No risky deploys.

## Cut lines (apply in this order)

1. **Phase 5 still open on 18 Nov:** rules-only tagging (no LLM pass) for the rest of the catalog.
2. **Phase 7 still open on 22 Nov:** shop the look returns matches by category + colour only.
3. **Phase 9 not started by 24 Nov:** no chat at launch; keep "Complete the look" from rules.
4. **Never cut:** server-side collection, the real-drop tests, KVKK basics (including photo
   handling), honest "tracking since" wording.

## After launch (not before)

My wardrobe (save owned pieces, mix with new ones); optional login to sync the profile; image
similarity search (SigLIP) for shop the look; per-size price alerts (Telegram); men/women chooser.
Price forecasting once there are 3+ months of history; cross-brand matching; more brands and regions;
English UI; affiliate integration; Langfuse tracing; partitioning `price_observations` if needed.
