"use client";

import { useState, useRef, useCallback } from "react";

interface Props {
  beforeSrc: string;
  afterSrc: string;
  beforeLabel?: string;
  afterLabel?: string;
}

export default function ImageCompare({
  beforeSrc,
  afterSrc,
  beforeLabel = "Original",
  afterLabel = "Processed",
}: Props) {
  const [position, setPosition] = useState(50);
  const containerRef = useRef<HTMLDivElement>(null);
  const dragging = useRef(false);

  const updatePosition = useCallback((clientX: number) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    const x = clientX - rect.left;
    const pct = Math.max(0, Math.min(100, (x / rect.width) * 100));
    setPosition(pct);
  }, []);

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    dragging.current = true;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    updatePosition(e.clientX);
  }, [updatePosition]);

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    if (!dragging.current) return;
    updatePosition(e.clientX);
  }, [updatePosition]);

  const handlePointerUp = useCallback(() => {
    dragging.current = false;
  }, []);

  return (
    <div
      ref={containerRef}
      className="relative w-full overflow-hidden rounded border cursor-col-resize select-none touch-none"
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
    >
      {/* After image (full width, visible background) */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={afterSrc} alt={afterLabel} className="w-full block" draggable={false} />

      {/* Before image (clipped by slider position) */}
      <div
        className="absolute inset-0 overflow-hidden"
        style={{ width: `${position}%` }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={beforeSrc}
          alt={beforeLabel}
          className="w-full block"
          style={{ width: containerRef.current ? `${containerRef.current.offsetWidth}px` : "100%" }}
          draggable={false}
        />
      </div>

      {/* Slider line */}
      <div
        className="absolute top-0 bottom-0 w-0.5 bg-white shadow-lg"
        style={{ left: `${position}%`, transform: "translateX(-50%)" }}
      >
        {/* Handle */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-8 h-8 bg-white rounded-full shadow-lg flex items-center justify-center">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="#666" strokeWidth="2">
            <path d="M4 2L1 7L4 12" />
            <path d="M10 2L13 7L10 12" />
          </svg>
        </div>
      </div>

      {/* Labels */}
      <div className="absolute top-2 left-2 px-2 py-0.5 bg-black/60 text-white text-xs rounded">
        {beforeLabel}
      </div>
      <div className="absolute top-2 right-2 px-2 py-0.5 bg-black/60 text-white text-xs rounded">
        {afterLabel}
      </div>
    </div>
  );
}
