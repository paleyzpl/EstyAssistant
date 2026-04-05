"use client";

import { useState, useCallback } from "react";
import {
  getUploadUrl,
  uploadToS3,
  processImage,
  generateListing,
  generateMockups,
  type ProcessedImage,
  type ListingMetadata,
  type MockupImage,
} from "@/lib/api";
import ListingEditor from "@/components/ListingEditor";
import MockupGallery from "@/components/MockupGallery";

const AVAILABLE_SIZES = ["5x7", "8x10", "11x14", "16x20"];

type ProcessStatus = "idle" | "uploading" | "processing" | "done" | "error";
type ListingStatus = "idle" | "generating" | "done" | "error";
type MockupStatus = "idle" | "generating" | "done" | "error";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [previewSrc, setPreviewSrc] = useState<string | null>(null);
  const [selectedSizes, setSelectedSizes] = useState<string[]>(["8x10"]);
  const [processStatus, setProcessStatus] = useState<ProcessStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [outputs, setOutputs] = useState<ProcessedImage[]>([]);
  const [processedPreview, setProcessedPreview] = useState<string | null>(null);
  const [s3Key, setS3Key] = useState<string | null>(null);
  const [processedS3Key, setProcessedS3Key] = useState<string | null>(null);

  // Listing state
  const [listingStatus, setListingStatus] = useState<ListingStatus>("idle");
  const [listing, setListing] = useState<ListingMetadata | null>(null);

  // Mockup state
  const [mockupStatus, setMockupStatus] = useState<MockupStatus>("idle");
  const [mockups, setMockups] = useState<MockupImage[]>([]);

  const resetAll = () => {
    setOutputs([]);
    setProcessedPreview(null);
    setError(null);
    setProcessStatus("idle");
    setS3Key(null);
    setProcessedS3Key(null);
    setListing(null);
    setListingStatus("idle");
    setMockups([]);
    setMockupStatus("idle");
  };

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const f = e.target.files?.[0];
      if (!f) return;
      setFile(f);
      setPreviewSrc(URL.createObjectURL(f));
      resetAll();
    },
    []
  );

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0];
    if (!f) return;
    setFile(f);
    setPreviewSrc(URL.createObjectURL(f));
    resetAll();
  }, []);

  const toggleSize = (size: string) => {
    setSelectedSizes((prev) =>
      prev.includes(size) ? prev.filter((s) => s !== size) : [...prev, size]
    );
  };

  const handleProcess = async () => {
    if (!file) return;
    setError(null);

    try {
      setProcessStatus("uploading");
      const { upload_url, s3_key } = await getUploadUrl(file.type);
      setS3Key(s3_key);
      await uploadToS3(upload_url, file);

      setProcessStatus("processing");
      const result = await processImage(s3_key, selectedSizes);

      setProcessedPreview(result.preview_url);
      setOutputs(result.outputs);
      // Use first output's S3 key for listing/mockups
      if (result.outputs.length > 0) {
        setProcessedS3Key(s3_key);
      }
      setProcessStatus("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setProcessStatus("error");
    }
  };

  const handleGenerateListing = async () => {
    if (!s3Key) return;
    setError(null);

    try {
      setListingStatus("generating");
      const result = await generateListing(s3Key);
      setListing(result);
      setListingStatus("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Listing generation failed");
      setListingStatus("error");
    }
  };

  const handleGenerateMockups = async () => {
    if (!s3Key) return;
    setError(null);

    try {
      setMockupStatus("generating");
      const result = await generateMockups(s3Key);
      setMockups(result.mockups);
      setMockupStatus("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Mockup generation failed");
      setMockupStatus("error");
    }
  };

  const isProcessed = processStatus === "done";

  return (
    <main className="max-w-4xl mx-auto px-4 py-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold">Carrot Sketches</h1>
        <p className="text-gray-600 mt-1">
          Process pen &amp; ink sketches into print-ready downloads
        </p>
      </header>

      {/* Upload Area */}
      <section className="mb-6">
        <div
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-gray-500 transition-colors"
        >
          <input
            type="file"
            accept="image/*"
            onChange={handleFileChange}
            className="hidden"
            id="file-input"
          />
          <label htmlFor="file-input" className="cursor-pointer">
            {file ? (
              <p className="text-gray-700">
                Selected: <strong>{file.name}</strong> (
                {(file.size / 1024 / 1024).toFixed(1)} MB)
              </p>
            ) : (
              <div>
                <p className="text-gray-500 text-lg mb-2">
                  Drop a sketch here or click to browse
                </p>
                <p className="text-gray-400 text-sm">
                  Supports JPEG, PNG, WEBP
                </p>
              </div>
            )}
          </label>
        </div>
      </section>

      {/* Size Selector */}
      <section className="mb-6">
        <h2 className="text-lg font-semibold mb-2">Print Sizes</h2>
        <div className="flex gap-3 flex-wrap">
          {AVAILABLE_SIZES.map((size) => (
            <button
              key={size}
              onClick={() => toggleSize(size)}
              className={`px-4 py-2 rounded border transition-colors ${
                selectedSizes.includes(size)
                  ? "bg-black text-white border-black"
                  : "bg-white text-gray-700 border-gray-300 hover:border-gray-500"
              }`}
            >
              {size}&quot;
            </button>
          ))}
        </div>
      </section>

      {/* Process Button */}
      <section className="mb-8">
        <button
          onClick={handleProcess}
          disabled={!file || processStatus === "uploading" || processStatus === "processing"}
          className="bg-black text-white px-6 py-3 rounded-lg font-medium disabled:opacity-40 disabled:cursor-not-allowed hover:bg-gray-800 transition-colors"
        >
          {processStatus === "uploading"
            ? "Uploading..."
            : processStatus === "processing"
              ? "Processing..."
              : "Process Sketch"}
        </button>
      </section>

      {/* Error */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Before / After Preview */}
      {(previewSrc || processedPreview) && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-4">Preview</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {previewSrc && (
              <div>
                <p className="text-sm text-gray-500 mb-2">Original</p>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={previewSrc}
                  alt="Original sketch"
                  className="w-full rounded border"
                />
              </div>
            )}
            {processedPreview && (
              <div>
                <p className="text-sm text-gray-500 mb-2">Processed</p>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={processedPreview}
                  alt="Processed sketch"
                  className="w-full rounded border"
                />
              </div>
            )}
          </div>
        </section>
      )}

      {/* Download Links */}
      {outputs.length > 0 && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-3">Downloads</h2>
          <div className="flex gap-3 flex-wrap">
            {outputs.map((output) => (
              <a
                key={output.size}
                href={output.download_url}
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50 transition-colors"
              >
                {output.size}&quot; PNG
              </a>
            ))}
          </div>
        </section>
      )}

      {/* Post-processing actions */}
      {isProcessed && (
        <section className="mb-8">
          <div className="flex gap-3 flex-wrap">
            {listingStatus === "idle" && (
              <button
                onClick={handleGenerateListing}
                className="bg-black text-white px-5 py-2.5 rounded-lg font-medium hover:bg-gray-800 transition-colors"
              >
                Generate Listing
              </button>
            )}
            {listingStatus === "generating" && (
              <button disabled className="bg-gray-400 text-white px-5 py-2.5 rounded-lg font-medium">
                Generating Listing...
              </button>
            )}

            {mockupStatus === "idle" && (
              <button
                onClick={handleGenerateMockups}
                className="border border-black text-black px-5 py-2.5 rounded-lg font-medium hover:bg-gray-50 transition-colors"
              >
                Generate Mockups
              </button>
            )}
            {mockupStatus === "generating" && (
              <button disabled className="border border-gray-300 text-gray-400 px-5 py-2.5 rounded-lg font-medium">
                Generating Mockups...
              </button>
            )}
          </div>
        </section>
      )}

      {/* Listing Editor */}
      {listing && (
        <section className="mb-8">
          <ListingEditor initial={listing} onChange={setListing} />
        </section>
      )}

      {/* Mockup Gallery */}
      {(mockupStatus === "generating" || mockups.length > 0) && (
        <section className="mb-8">
          <MockupGallery
            mockups={mockups}
            loading={mockupStatus === "generating"}
          />
        </section>
      )}
    </main>
  );
}
