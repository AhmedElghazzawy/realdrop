# LC Waikiki (`lc-waikiki`)

**Recommendation: no-go.** Owner decision: _pending_

- Base URL: `https://www.lcw.com` (`www.lcwaikiki.com` redirects here)
- Checked: 24 Oct 2026

## robots.txt

`User-agent: *` / `Allow: /`. Product sitemap points to a feed at `api.lcwaikiki.com` (20 files).

## Terms (the blocker)

`/statik/kullanimkosullari` forbids, under user obligations, accessing content with "otomatik program,
webcrawler, örümcek, robot, veri madenciliği (data mining) ve veri taraması (data crawling)" and
"screen scraping" software, and says site content is "tamamen kişisel ve ticari amaçlı olmayan
kullanım için". robots.txt allows it, but the terms forbid it explicitly, so we stay out.

Could become a go only with written permission or an affiliate/data feed.

## Data (for reference)

Product pages have schema.org `Product` JSON-LD with a size list and one offer; per-size stock is not
in the HTML.
