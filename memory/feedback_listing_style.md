---
name: Etsy Listing Style Preferences
description: User's shop is Carrot Sketches - specific title format, description structure with ✦ headers, warm concise tone
type: feedback
---

Shop name is "Carrot Sketches". All listings end with © Carrot Sketches – Personal use only.

Title format: `[Subject] Ink Sketch | Black and White [Category] Wall Art | [Location/Theme] Printable Drawing`
**Why:** Matches user's best-selling listing (Jefferson Memorial). Pipe-separated, keyword-rich.
**How to apply:** Follow this exact pattern in the SYSTEM_PROMPT for Claude API.

Description must use ✦ section headers (not bullet points or markdown).
**Why:** User said "you are doing bullet point" when I initially used plain paragraphs. Etsy doesn't support HTML/markdown, so Unicode symbols are the standard.
**How to apply:** Use ✦ SECTION NAME ✦ format with • for bullets within sections.

Description should be 300-400 words, warm and concise — NOT 100-150 words (too short) and NOT 600+ words (too long).
**Why:** Research showed Etsy SEO benefits from 300-600 words. User's original listing was ~100 words which is too short for SEO.
**How to apply:** Include sections: hook, what's included, how it works, printing tips, styling ideas, please note, copyright.

Don't generate descriptions that are too corporate/generic. Match the warm personal tone of the existing shop.
