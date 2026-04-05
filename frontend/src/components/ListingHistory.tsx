"use client";

import { useState, useEffect } from "react";
import {
  getListings,
  deleteListing,
  type SavedListing,
  type ListingMetadata,
} from "@/lib/api";

interface Props {
  onLoad: (listing: SavedListing) => void;
  refreshKey: number;
}

export default function ListingHistory({ onLoad, refreshKey }: Props) {
  const [listings, setListings] = useState<SavedListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    setLoading(true);
    getListings(20)
      .then(setListings)
      .catch(() => setListings([]))
      .finally(() => setLoading(false));
  }, [refreshKey]);

  const handleDelete = async (id: string) => {
    try {
      await deleteListing(id);
      setListings((prev) => prev.filter((l) => l.id !== id));
    } catch {
      // ignore
    }
  };

  if (loading) return null;
  if (listings.length === 0) return null;

  const formatDate = (ts: number) => {
    if (!ts) return "";
    return new Date(ts * 1000).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  return (
    <div className="border rounded-lg">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-gray-50 transition-colors"
      >
        <span className="font-semibold text-sm">
          Listing History ({listings.length})
        </span>
        <span className="text-gray-400 text-xs">{expanded ? "Hide" : "Show"}</span>
      </button>

      {expanded && (
        <div className="border-t divide-y max-h-80 overflow-y-auto">
          {listings.map((item) => (
            <div
              key={item.id}
              className="px-4 py-3 flex items-center justify-between gap-3 hover:bg-gray-50"
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{item.title}</p>
                <p className="text-xs text-gray-400">
                  {formatDate(item.created_at)}
                  {item.price != null && ` \u00b7 $${item.price.toFixed(2)}`}
                  {item.etsy_listing_url && " \u00b7 Published"}
                  {item.sizes.length > 0 && ` \u00b7 ${item.sizes.join(", ")}`}
                </p>
              </div>
              <div className="flex gap-2 shrink-0">
                <button
                  onClick={() => onLoad(item)}
                  className="text-xs px-3 py-1 border rounded hover:bg-gray-100 transition-colors"
                >
                  Load
                </button>
                <button
                  onClick={() => handleDelete(item.id)}
                  className="text-xs px-2 py-1 text-gray-400 hover:text-red-500 transition-colors"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
