"use client";

import type { MockupImage } from "@/lib/api";

interface Props {
  mockups: MockupImage[];
  loading?: boolean;
}

export default function MockupGallery({ mockups, loading }: Props) {
  if (loading) {
    return (
      <div>
        <h2 className="text-base sm:text-lg font-semibold mb-3">Frame Mockups</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="border rounded overflow-hidden animate-pulse">
              <div className="bg-gray-200 aspect-[3/4]"></div>
              <div className="px-3 py-2">
                <div className="h-3 bg-gray-200 rounded w-24"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (mockups.length === 0) return null;

  return (
    <div>
      <h2 className="text-base sm:text-lg font-semibold mb-3">Frame Mockups</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
        {mockups.map((m) => (
          <div key={m.template_name} className="border rounded overflow-hidden">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={m.url}
              alt={`Mockup: ${m.template_name}`}
              className="w-full"
            />
            <div className="px-3 py-2 text-xs text-gray-500">
              {m.template_name.replace(/_/g, " ")}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
