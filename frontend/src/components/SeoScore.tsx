"use client";

import type { ListingMetadata } from "@/lib/api";

interface Props {
  listing: ListingMetadata;
}

interface Check {
  label: string;
  pass: boolean;
  detail: string;
}

function scoreListing(listing: ListingMetadata): { score: number; checks: Check[] } {
  const checks: Check[] = [];

  // Title length (ideal: 80-140 chars)
  const titleLen = listing.title.length;
  checks.push({
    label: "Title length",
    pass: titleLen >= 80 && titleLen <= 140,
    detail: `${titleLen}/140 chars${titleLen < 80 ? " (too short, aim for 80+)" : titleLen > 140 ? " (over limit!)" : " (good)"}`,
  });

  // Title has pipe separators (Etsy best practice)
  const pipes = (listing.title.match(/\|/g) || []).length;
  checks.push({
    label: "Pipe-separated keywords",
    pass: pipes >= 2,
    detail: `${pipes} pipe separator(s)${pipes < 2 ? " (use 2-3 for keyword variety)" : " (good)"}`,
  });

  // Tag count (ideal: 13)
  checks.push({
    label: "Tag count",
    pass: listing.tags.length >= 10,
    detail: `${listing.tags.length}/13 tags${listing.tags.length < 10 ? " (add more tags)" : " (good)"}`,
  });

  // Tag diversity (no duplicates, no single-word overlap)
  const uniqueTags = new Set(listing.tags.map((t) => t.toLowerCase()));
  checks.push({
    label: "Tag uniqueness",
    pass: uniqueTags.size === listing.tags.length,
    detail: uniqueTags.size < listing.tags.length
      ? `${listing.tags.length - uniqueTags.size} duplicate(s) found`
      : "All tags unique",
  });

  // Multi-word tags (Etsy favors multi-word phrases)
  const multiWord = listing.tags.filter((t) => t.includes(" ")).length;
  checks.push({
    label: "Multi-word tags",
    pass: multiWord >= listing.tags.length * 0.6,
    detail: `${multiWord}/${listing.tags.length} are phrases${multiWord < listing.tags.length * 0.6 ? " (use more 2-3 word phrases)" : " (good)"}`,
  });

  // Description length (ideal: 300+ words)
  const wordCount = listing.description.split(/\s+/).length;
  checks.push({
    label: "Description length",
    pass: wordCount >= 200,
    detail: `~${wordCount} words${wordCount < 200 ? " (aim for 300+)" : " (good)"}`,
  });

  // Has section headers
  const hasSections = listing.description.includes("✦");
  checks.push({
    label: "Structured sections",
    pass: hasSections,
    detail: hasSections ? "Has section headers" : "Add ✦ section headers",
  });

  // First 160 chars (Etsy shows this before "Read more")
  const firstLine = listing.description.split("\n")[0];
  checks.push({
    label: "Opening hook",
    pass: firstLine.length >= 100 && firstLine.length <= 200,
    detail: `${firstLine.length} chars${firstLine.length < 100 ? " (too short for Read More preview)" : " (good)"}`,
  });

  const passed = checks.filter((c) => c.pass).length;
  const score = Math.round((passed / checks.length) * 100);

  return { score, checks };
}

export default function SeoScore({ listing }: Props) {
  const { score, checks } = scoreListing(listing);

  const color = score >= 80 ? "text-green-600" : score >= 50 ? "text-yellow-600" : "text-red-600";
  const bg = score >= 80 ? "bg-green-50" : score >= 50 ? "bg-yellow-50" : "bg-red-50";

  return (
    <div className={`${bg} rounded-lg p-3 sm:p-4`}>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold">SEO Score</h3>
        <span className={`text-lg font-bold ${color}`}>{score}%</span>
      </div>
      <div className="space-y-1">
        {checks.map((check, i) => (
          <div key={i} className="flex items-start gap-2 text-xs">
            <span className={check.pass ? "text-green-500" : "text-red-400"}>
              {check.pass ? "\u2713" : "\u2717"}
            </span>
            <span className="text-[var(--muted)]">
              <strong>{check.label}:</strong> {check.detail}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
