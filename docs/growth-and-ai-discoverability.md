# Growth and AI discoverability (SEO / AEO / GEO)

Discovery through ChatGPT, Claude and Gemini matters, so this is its own workstream.

## Website content structure
```
/
├── /berlin
├── /berlin/this-weekend
├── /berlin/date-ideas
├── /berlin/family-activities
├── /berlin/friends-weekend
├── /berlin/under-50-euros
├── /berlin/unusual-experiences
└── /guides
    ├── /how-to-plan-a-date-in-berlin
    ├── /indoor-family-activities-berlin
    └── /weekend-ideas-berlin
```
Every page must answer a real question, contain verifiable facts with sources, and link into the discovery experience. No thin or duplicated SEO pages. Preserve the site's editorial design and emotional positioning.

## AI crawler readiness
- Public pages accessible without login.
- Correct canonical URLs.
- `sitemap.xml` and `robots.txt`.
- Fast server-rendered or prerendered content (CloudFront in front of prerendered pages).
- Useful titles, descriptions and accurate structured data.
- No indexing of private admin pages or user-specific collections.
- No fabricated reviews or ratings.

Example robots policy:
```txt
User-agent: OAI-SearchBot
Allow: /

User-agent: *
Allow: /
Sitemap: https://YOUR-DOMAIN/sitemap.xml
```
Review each crawler policy against the content you allow to be used: OpenAI distinguishes `OAI-SearchBot` (search) from `GPTBot` (model training).

## Measurement
An analytics dashboard (Gold `channel_performance_daily`) covering Google/Bing organic, AI referral traffic where detectable, social referrals, paid campaigns, direct and referral traffic, branded vs non-branded search.

Do not claim that every AI-generated recommendation can be tracked: the referrer is not guaranteed in every case.
