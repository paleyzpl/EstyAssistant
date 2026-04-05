---
name: Photo Quality and Processing Preferences
description: User preferences for image processing - outdoor photos preferred, smooth lines, preserve shadow detail
type: feedback
---

Outdoor photos (even with color tint) produce far better results than indoor photos.
**Why:** Indoor photos have uneven lighting that creates paper texture artifacts. Outdoor sunlight gives even, strong lighting with better ink-to-paper contrast. Color tints don't matter since pipeline converts to grayscale.
**How to apply:** Recommend outdoor photography when user asks about photo tips.

Lines should be smooth, not over-sharpened. Preserve natural pen stroke softness.
**Why:** User said "the line is a bit too sharp, doesn't preserve smoothness from original picture" when sharpening was too aggressive.
**How to apply:** Keep unsharp mask gentle (1.15/−0.15 with sigma 1.5). Don't add ink darkening in background step.

Shadow and hatching detail must be preserved — don't erase light strokes.
**Why:** User said "you removed too much lines in the shadows, it is not dark enough as original picture" when bg_adaptive_c was set to 15.
**How to apply:** Keep bg_adaptive_c at 8 (not higher). Better to retain some paper texture than lose artistic detail.
