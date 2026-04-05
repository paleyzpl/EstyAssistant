"use client";

import { useState, useCallback, useEffect } from "react";
import {
  getUploadUrl,
  uploadToS3,
  processImage,
  generateListing,
  generateMockups,
  getEtsyAuthStatus,
  startEtsyAuth,
  disconnectEtsy,
  publishListing,
  getJobStatus,
  type ProcessedImage,
  type ListingMetadata,
  type MockupImage,
  type AuthStatus,
  type JobStatus,
} from "@/lib/api";
import ListingEditor from "@/components/ListingEditor";
import MockupGallery from "@/components/MockupGallery";

const AVAILABLE_SIZES = ["5x7", "8x10", "11x14", "16x20"];

type ProcessStatus = "idle" | "uploading" | "processing" | "done" | "error";
type ListingStatus = "idle" | "generating" | "done" | "error";
type MockupStatus = "idle" | "generating" | "done" | "error";
type PublishStatus = "idle" | "publishing" | "done" | "error";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [previewSrc, setPreviewSrc] = useState<string | null>(null);
  const [selectedSizes, setSelectedSizes] = useState<string[]>(["8x10"]);
  const [processStatus, setProcessStatus] = useState<ProcessStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [outputs, setOutputs] = useState<ProcessedImage[]>([]);
  const [processedPreview, setProcessedPreview] = useState<string | null>(null);
  const [s3Key, setS3Key] = useState<string | null>(null);

  // Listing state
  const [listingStatus, setListingStatus] = useState<ListingStatus>("idle");
  const [listing, setListing] = useState<ListingMetadata | null>(null);

  // Mockup state
  const [mockupStatus, setMockupStatus] = useState<MockupStatus>("idle");
  const [mockups, setMockups] = useState<MockupImage[]>([]);

  // Etsy auth state
  const [etsyStatus, setEtsyStatus] = useState<AuthStatus | null>(null);

  // Publish state
  const [publishStatus, setPublishStatus] = useState<PublishStatus>("idle");
  const [publishResult, setPublishResult] = useState<JobStatus["result"] | null>(null);
  const [price, setPrice] = useState("4.99");

  // Check Etsy connection on load
  useEffect(() => {
    getEtsyAuthStatus()
      .then(setEtsyStatus)
      .catch(() => setEtsyStatus({ connected: false, shop_id: null }));
  }, []);

  const resetAll = () => {
    setOutputs([]);
    setProcessedPreview(null);
    setError(null);
    setProcessStatus("idle");
    setS3Key(null);
    setListing(null);
    setListingStatus("idle");
    setMockups([]);
    setMockupStatus("idle");
    setPublishStatus("idle");
    setPublishResult(null);
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

  const handleConnectEtsy = async () => {
    try {
      const authUrl = await startEtsyAuth();
      window.location.href = authUrl;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start Etsy auth");
    }
  };

  const handleDisconnectEtsy = async () => {
    try {
      await disconnectEtsy();
      setEtsyStatus({ connected: false, shop_id: null });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to disconnect");
    }
  };

  const handlePublish = async () => {
    if (!s3Key || !listing) return;
    setError(null);

    try {
      setPublishStatus("publishing");
      const jobId = await publishListing({
        s3_key: s3Key,
        sizes: selectedSizes,
        title: listing.title,
        description: listing.description,
        tags: listing.tags,
        price: parseFloat(price),
      });

      // Poll for completion
      const poll = async () => {
        const status = await getJobStatus(jobId);
        if (status.status === "completed") {
          setPublishResult(status.result ?? null);
          setPublishStatus("done");
        } else if (status.status === "failed") {
          setError(status.error || "Publish failed");
          setPublishStatus("error");
        } else {
          setTimeout(poll, 2000);
        }
      };
      poll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Publish failed");
      setPublishStatus("error");
    }
  };

  const isProcessed = processStatus === "done";
  const canPublish = isProcessed && listing && etsyStatus?.connected && publishStatus === "idle";

  return (
    <main className="max-w-4xl mx-auto px-4 py-8">
      <header className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold">Carrot Sketches</h1>
          <p className="text-gray-600 mt-1">
            Process pen &amp; ink sketches into print-ready downloads
          </p>
        </div>

        {/* Etsy Connection Status */}
        <div className="text-right">
          {etsyStatus?.connected ? (
            <div>
              <span className="inline-block w-2 h-2 bg-green-500 rounded-full mr-1.5"></span>
              <span className="text-sm text-gray-600">Etsy connected</span>
              <button
                onClick={handleDisconnectEtsy}
                className="block text-xs text-gray-400 hover:text-red-500 mt-1"
              >
                Disconnect
              </button>
            </div>
          ) : (
            <button
              onClick={handleConnectEtsy}
              className="px-4 py-2 border border-orange-500 text-orange-600 rounded-lg text-sm font-medium hover:bg-orange-50 transition-colors"
            >
              Connect Etsy
            </button>
          )}
        </div>
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
                <img src={previewSrc} alt="Original sketch" className="w-full rounded border" />
              </div>
            )}
            {processedPreview && (
              <div>
                <p className="text-sm text-gray-500 mb-2">Processed</p>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={processedPreview} alt="Processed sketch" className="w-full rounded border" />
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
          <MockupGallery mockups={mockups} loading={mockupStatus === "generating"} />
        </section>
      )}

      {/* Publish to Etsy */}
      {listing && etsyStatus?.connected && (
        <section className="mb-8 p-6 border rounded-lg bg-gray-50">
          <h2 className="text-lg font-semibold mb-4">Publish to Etsy</h2>

          <div className="flex items-center gap-4 mb-4">
            <label className="text-sm text-gray-600">Price ($)</label>
            <input
              type="number"
              value={price}
              step="0.01"
              min="0.20"
              onChange={(e) => setPrice(e.target.value)}
              className="w-24 border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-black"
            />
          </div>

          {publishStatus === "idle" && (
            <button
              onClick={handlePublish}
              disabled={!canPublish}
              className="bg-orange-500 text-white px-6 py-3 rounded-lg font-medium hover:bg-orange-600 disabled:opacity-40 transition-colors"
            >
              Publish as Draft on Etsy
            </button>
          )}

          {publishStatus === "publishing" && (
            <div className="flex items-center gap-3">
              <div className="w-5 h-5 border-2 border-orange-500 border-t-transparent rounded-full animate-spin"></div>
              <span className="text-gray-600">Publishing to Etsy...</span>
            </div>
          )}

          {publishStatus === "done" && publishResult && (
            <div className="p-4 bg-green-50 border border-green-200 rounded">
              <p className="text-green-800 font-medium">Draft listing created!</p>
              {publishResult.listing_url && (
                <a
                  href={publishResult.listing_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-green-700 underline text-sm mt-1 block"
                >
                  View on Etsy
                </a>
              )}
            </div>
          )}

          {publishStatus === "error" && (
            <button
              onClick={() => setPublishStatus("idle")}
              className="text-sm text-gray-500 underline"
            >
              Try again
            </button>
          )}
        </section>
      )}

      {/* Prompt to connect Etsy */}
      {listing && !etsyStatus?.connected && (
        <section className="mb-8 p-6 border border-dashed border-orange-300 rounded-lg text-center">
          <p className="text-gray-600 mb-3">Connect your Etsy shop to publish listings</p>
          <button
            onClick={handleConnectEtsy}
            className="px-5 py-2.5 bg-orange-500 text-white rounded-lg font-medium hover:bg-orange-600 transition-colors"
          >
            Connect Etsy
          </button>
        </section>
      )}
    </main>
  );
}
