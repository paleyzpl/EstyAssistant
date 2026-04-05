"use client";

import { useState } from "react";
import type { ListingMetadata } from "@/lib/api";

interface Props {
  initial: ListingMetadata;
  onChange: (listing: ListingMetadata) => void;
}

export default function ListingEditor({ initial, onChange }: Props) {
  const [title, setTitle] = useState(initial.title);
  const [tags, setTags] = useState<string[]>(initial.tags);
  const [description, setDescription] = useState(initial.description);
  const [tagInput, setTagInput] = useState("");

  const update = (partial: Partial<ListingMetadata>) => {
    const next = {
      title: partial.title ?? title,
      tags: partial.tags ?? tags,
      description: partial.description ?? description,
    };
    onChange(next);
  };

  const addTag = () => {
    const t = tagInput.trim().slice(0, 20);
    if (t && tags.length < 13 && !tags.includes(t)) {
      const next = [...tags, t];
      setTags(next);
      setTagInput("");
      update({ tags: next });
    }
  };

  const removeTag = (index: number) => {
    const next = tags.filter((_, i) => i !== index);
    setTags(next);
    update({ tags: next });
  };

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Etsy Listing</h2>

      {/* Title */}
      <div>
        <label className="block text-sm text-gray-600 mb-1">
          Title ({title.length}/140)
        </label>
        <input
          type="text"
          value={title}
          maxLength={140}
          onChange={(e) => {
            setTitle(e.target.value);
            update({ title: e.target.value });
          }}
          className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-black"
        />
      </div>

      {/* Tags */}
      <div>
        <label className="block text-sm text-gray-600 mb-1">
          Tags ({tags.length}/13)
        </label>
        <div className="flex flex-wrap gap-2 mb-2">
          {tags.map((tag, i) => (
            <span
              key={i}
              className="inline-flex items-center gap-1 bg-gray-100 text-gray-700 px-2 py-1 rounded text-sm"
            >
              {tag}
              <button
                onClick={() => removeTag(i)}
                className="text-gray-400 hover:text-red-500"
              >
                x
              </button>
            </span>
          ))}
        </div>
        {tags.length < 13 && (
          <div className="flex gap-2">
            <input
              type="text"
              value={tagInput}
              maxLength={20}
              placeholder="Add a tag..."
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addTag())}
              className="flex-1 border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-black"
            />
            <button
              onClick={addTag}
              disabled={!tagInput.trim()}
              className="px-3 py-1.5 border rounded text-sm hover:bg-gray-50 disabled:opacity-40"
            >
              Add
            </button>
          </div>
        )}
      </div>

      {/* Description */}
      <div>
        <label className="block text-sm text-gray-600 mb-1">Description</label>
        <textarea
          value={description}
          rows={10}
          onChange={(e) => {
            setDescription(e.target.value);
            update({ description: e.target.value });
          }}
          className="w-full border rounded px-3 py-2 text-sm font-mono leading-relaxed focus:outline-none focus:ring-2 focus:ring-black"
        />
      </div>
    </div>
  );
}
