"use client";

import { useEffect } from "react";

interface Props {
  onProcess?: () => void;
  onSave?: () => void;
  onGenerateListing?: () => void;
}

export default function KeyboardShortcuts({ onProcess, onSave, onGenerateListing }: Props) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const ctrl = e.ctrlKey || e.metaKey;
      if (!ctrl) return;

      if (e.key === "Enter" && onProcess) {
        e.preventDefault();
        onProcess();
      } else if (e.key === "s" && onSave) {
        e.preventDefault();
        onSave();
      } else if (e.key === "g" && onGenerateListing) {
        e.preventDefault();
        onGenerateListing();
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onProcess, onSave, onGenerateListing]);

  return null;
}
