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
  saveListing as saveListingApi,
  type ProcessedImage,
  type ListingMetadata,
  type MockupImage,
  type AuthStatus,
  type JobStatus,
  type SavedListing,
} from "@/lib/api";
import ListingEditor from "@/components/ListingEditor";
import MockupGallery from "@/components/MockupGallery";
import ListingHistory from "@/components/ListingHistory";
import ToastContainer, { createToast, type ToastMessage } from "@/components/Toast";

const AVAILABLE_SIZES = ["5x7", "8x10", "11x14", "16x20"];

type ProcessStatus = "idle" | "uploading" | "processing" | "done" | "error";
type ListingStatus = "idle" | "generating" | "done" | "error";
type MockupStatus = "idle" | "generating" | "done" | "error";
type PublishStatus = "idle" | "publishing" | "done" | "error";

export default function Home() {
  // Files (batch support)
  const [files, setFiles] = useState<File[]>([]);
  const [currentFileIndex, setCurrentFileIndex] = useState(0);
  const [previewSrcs, setPreviewSrcs] = useState<string[]>([]);

  const [selectedSizes, setSelectedSizes] = useState<string[]>(["8x10"]);
  const [processStatus, setProcessStatus] = useState<ProcessStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [outputs, setOutputs] = useState<ProcessedImage[]>([]);
  const [processedPreview, setProcessedPreview] = useState<string | null>(null);
  const [s3Key, setS3Key] = useState<string | null>(null);

  // Batch progress
  const [batchProgress, setBatchProgress] = useState<{ current: number; total: number } | null>(null);

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

  // History state
  const [historyRefreshKey, setHistoryRefreshKey] = useState(0);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved">("idle");

  // Toast state
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const addToast = useCallback((type: ToastMessage["type"], text: string) => {
    setToasts((prev) => [...prev, createToast(type, text)]);
  }, []);
  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

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
    setBatchProgress(null);
  };

  const handleFiles = useCallback((newFiles: File[]) => {
    const imageFiles = newFiles.filter((f) => f.type.startsWith("image/"));
    if (imageFiles.length === 0) return;
    setFiles(imageFiles);
    setCurrentFileIndex(0);
    setPreviewSrcs(imageFiles.map((f) => URL.createObjectURL(f)));
    resetAll();
  }, []);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const newFiles = Array.from(e.target.files || []);
      handleFiles(newFiles);
    },
    [handleFiles]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const newFiles = Array.from(e.dataTransfer.files);
      handleFiles(newFiles);
    },
    [handleFiles]
  );

  const toggleSize = (size: string) => {
    setSelectedSizes((prev) =>
      prev.includes(size) ? prev.filter((s) => s !== size) : [...prev, size]
    );
  };

  const handleProcess = async () => {
    if (files.length === 0) return;
    setError(null);

    const isBatch = files.length > 1;

    try {
      if (isBatch) {
        // Batch: process all files
        setProcessStatus("uploading");
        setBatchProgress({ current: 0, total: files.length });

        let lastKey = "";
        let allOutputs: ProcessedImage[] = [];
        let lastPreview = "";

        for (let i = 0; i < files.length; i++) {
          setBatchProgress({ current: i + 1, total: files.length });
          setCurrentFileIndex(i);

          const file = files[i];
          const { upload_url, s3_key } = await getUploadUrl(file.type);
          await uploadToS3(upload_url, file);

          if (i === 0) setProcessStatus("processing");

          const result = await processImage(s3_key, selectedSizes);
          allOutputs = [...allOutputs, ...result.outputs];
          lastPreview = result.preview_url;
          lastKey = s3_key;
        }

        setS3Key(lastKey);
        setProcessedPreview(lastPreview);
        setOutputs(allOutputs);
        setProcessStatus("done");
        setBatchProgress(null);
        addToast("success", `Processed ${files.length} sketches`);
      } else {
        // Single file
        const file = files[0];
        setProcessStatus("uploading");
        const { upload_url, s3_key } = await getUploadUrl(file.type);
        setS3Key(s3_key);
        await uploadToS3(upload_url, file);

        setProcessStatus("processing");
        const result = await processImage(s3_key, selectedSizes);

        setProcessedPreview(result.preview_url);
        setOutputs(result.outputs);
        setProcessStatus("done");
        addToast("success", "Sketch processed");
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setError(msg);
      setProcessStatus("error");
      addToast("error", msg);
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
      addToast("success", "Listing generated");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Listing generation failed";
      setError(msg);
      setListingStatus("error");
      addToast("error", msg);
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
      addToast("success", `${result.mockups.length} mockups generated`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Mockup generation failed";
      setError(msg);
      setMockupStatus("error");
      addToast("error", msg);
    }
  };

  const handleConnectEtsy = async () => {
    try {
      const authUrl = await startEtsyAuth();
      window.location.href = authUrl;
    } catch (err) {
      addToast("error", err instanceof Error ? err.message : "Failed to start Etsy auth");
    }
  };

  const handleDisconnectEtsy = async () => {
    try {
      await disconnectEtsy();
      setEtsyStatus({ connected: false, shop_id: null });
      addToast("info", "Etsy disconnected");
    } catch (err) {
      addToast("error", "Failed to disconnect");
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

      const poll = async () => {
        const status = await getJobStatus(jobId);
        if (status.status === "completed") {
          setPublishResult(status.result ?? null);
          setPublishStatus("done");
          addToast("success", "Published to Etsy!");
          // Auto-save to history
          await saveListingApi({
            title: listing.title,
            tags: listing.tags,
            description: listing.description,
            price: parseFloat(price),
            s3_key: s3Key,
            sizes: selectedSizes,
            etsy_listing_id: status.result?.listing_id,
            etsy_listing_url: status.result?.listing_url || undefined,
            preview_url: processedPreview || undefined,
          });
          setHistoryRefreshKey((k) => k + 1);
        } else if (status.status === "failed") {
          setError(status.error || "Publish failed");
          setPublishStatus("error");
          addToast("error", status.error || "Publish failed");
        } else {
          setTimeout(poll, 2000);
        }
      };
      poll();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Publish failed";
      setError(msg);
      setPublishStatus("error");
      addToast("error", msg);
    }
  };

  const handleSaveListing = async () => {
    if (!listing) return;
    setSaveStatus("saving");
    try {
      await saveListingApi({
        title: listing.title,
        tags: listing.tags,
        description: listing.description,
        price: price ? parseFloat(price) : undefined,
        s3_key: s3Key || undefined,
        sizes: selectedSizes,
        preview_url: processedPreview || undefined,
      });
      setSaveStatus("saved");
      setHistoryRefreshKey((k) => k + 1);
      addToast("success", "Listing saved");
      setTimeout(() => setSaveStatus("idle"), 2000);
    } catch {
      setSaveStatus("idle");
      addToast("error", "Failed to save listing");
    }
  };

  const handleLoadListing = (saved: SavedListing) => {
    setListing({
      title: saved.title,
      tags: saved.tags,
      description: saved.description,
    });
    setListingStatus("done");
    if (saved.price != null) setPrice(saved.price.toFixed(2));
    if (saved.s3_key) setS3Key(saved.s3_key);
    if (saved.sizes.length > 0) setSelectedSizes(saved.sizes);
    addToast("info", "Listing loaded");
  };

  const isProcessed = processStatus === "done";
  const canPublish = isProcessed && listing && etsyStatus?.connected && publishStatus === "idle";
  const currentFile = files[currentFileIndex] || null;
  const currentPreview = previewSrcs[currentFileIndex] || null;

  return (
    <main className="max-w-4xl mx-auto px-4 py-6 sm:py-8">
      {/* Toast Notifications */}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      <header className="mb-6 sm:mb-8 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold">Carrot Sketches</h1>
          <p className="text-gray-600 mt-1 text-sm sm:text-base">
            Process pen &amp; ink sketches into print-ready downloads
          </p>
        </div>

        {/* Etsy Connection Status */}
        <div className="sm:text-right">
          {etsyStatus?.connected ? (
            <div className="flex items-center gap-2 sm:justify-end">
              <span className="inline-block w-2 h-2 bg-green-500 rounded-full"></span>
              <span className="text-sm text-gray-600">Etsy connected</span>
              <button
                onClick={handleDisconnectEtsy}
                className="text-xs text-gray-400 hover:text-red-500 ml-1"
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
      <section className="mb-5">
        <div
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          className="border-2 border-dashed border-gray-300 rounded-lg p-6 sm:p-8 text-center cursor-pointer hover:border-gray-500 transition-colors"
        >
          <input
            type="file"
            accept="image/*"
            multiple
            onChange={handleFileChange}
            className="hidden"
            id="file-input"
          />
          <label htmlFor="file-input" className="cursor-pointer">
            {files.length > 0 ? (
              <p className="text-gray-700 text-sm sm:text-base">
                {files.length === 1 ? (
                  <>
                    Selected: <strong>{currentFile?.name}</strong> (
                    {((currentFile?.size || 0) / 1024 / 1024).toFixed(1)} MB)
                  </>
                ) : (
                  <>
                    <strong>{files.length} sketches</strong> selected (
                    {(files.reduce((sum, f) => sum + f.size, 0) / 1024 / 1024).toFixed(1)} MB total)
                  </>
                )}
              </p>
            ) : (
              <div>
                <p className="text-gray-500 text-base sm:text-lg mb-2">
                  Drop sketches here or click to browse
                </p>
                <p className="text-gray-400 text-xs sm:text-sm">
                  Supports JPEG, PNG, WEBP. Select multiple for batch processing.
                </p>
              </div>
            )}
          </label>
        </div>
      </section>

      {/* Size Selector */}
      <section className="mb-5">
        <h2 className="text-base sm:text-lg font-semibold mb-2">Print Sizes</h2>
        <div className="flex gap-2 sm:gap-3 flex-wrap">
          {AVAILABLE_SIZES.map((size) => (
            <button
              key={size}
              onClick={() => toggleSize(size)}
              className={`px-3 sm:px-4 py-1.5 sm:py-2 rounded border text-sm transition-colors ${
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
      <section className="mb-6 sm:mb-8">
        <button
          onClick={handleProcess}
          disabled={files.length === 0 || processStatus === "uploading" || processStatus === "processing"}
          className="w-full sm:w-auto bg-black text-white px-6 py-3 rounded-lg font-medium disabled:opacity-40 disabled:cursor-not-allowed hover:bg-gray-800 transition-colors"
        >
          {processStatus === "uploading"
            ? batchProgress
              ? `Uploading ${batchProgress.current}/${batchProgress.total}...`
              : "Uploading..."
            : processStatus === "processing"
              ? batchProgress
                ? `Processing ${batchProgress.current}/${batchProgress.total}...`
                : "Processing..."
              : files.length > 1
                ? `Process ${files.length} Sketches`
                : "Process Sketch"}
        </button>
      </section>

      {/* Error */}
      {error && (
        <div className="mb-5 p-3 sm:p-4 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Before / After Preview */}
      {(currentPreview || processedPreview) && (
        <section className="mb-6 sm:mb-8">
          <h2 className="text-base sm:text-lg font-semibold mb-3 sm:mb-4">Preview</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
            {currentPreview && (
              <div>
                <p className="text-xs sm:text-sm text-gray-500 mb-1.5">Original</p>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={currentPreview} alt="Original sketch" className="w-full rounded border" />
              </div>
            )}
            {processedPreview && (
              <div>
                <p className="text-xs sm:text-sm text-gray-500 mb-1.5">Processed</p>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={processedPreview} alt="Processed sketch" className="w-full rounded border" />
              </div>
            )}
          </div>
        </section>
      )}

      {/* Download Links */}
      {outputs.length > 0 && (
        <section className="mb-6 sm:mb-8">
          <h2 className="text-base sm:text-lg font-semibold mb-2 sm:mb-3">Downloads</h2>
          <div className="flex gap-2 sm:gap-3 flex-wrap">
            {outputs.map((output, i) => (
              <a
                key={`${output.size}-${i}`}
                href={output.download_url}
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 sm:px-4 py-1.5 sm:py-2 border border-gray-300 rounded hover:bg-gray-50 transition-colors text-sm"
              >
                {output.size}&quot; PNG
              </a>
            ))}
          </div>
        </section>
      )}

      {/* Post-processing actions */}
      {isProcessed && (
        <section className="mb-6 sm:mb-8">
          <div className="flex gap-2 sm:gap-3 flex-wrap">
            {listingStatus === "idle" && (
              <button
                onClick={handleGenerateListing}
                className="flex-1 sm:flex-none bg-black text-white px-5 py-2.5 rounded-lg font-medium hover:bg-gray-800 transition-colors text-sm"
              >
                Generate Listing
              </button>
            )}
            {listingStatus === "generating" && (
              <button disabled className="flex-1 sm:flex-none bg-gray-400 text-white px-5 py-2.5 rounded-lg font-medium text-sm flex items-center justify-center gap-2">
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                Generating Listing...
              </button>
            )}

            {mockupStatus === "idle" && (
              <button
                onClick={handleGenerateMockups}
                className="flex-1 sm:flex-none border border-black text-black px-5 py-2.5 rounded-lg font-medium hover:bg-gray-50 transition-colors text-sm"
              >
                Generate Mockups
              </button>
            )}
            {mockupStatus === "generating" && (
              <button disabled className="flex-1 sm:flex-none border border-gray-300 text-gray-400 px-5 py-2.5 rounded-lg font-medium text-sm flex items-center justify-center gap-2">
                <span className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin"></span>
                Generating Mockups...
              </button>
            )}
          </div>
        </section>
      )}

      {/* Listing Editor */}
      {listing && (
        <section className="mb-6 sm:mb-8">
          <ListingEditor initial={listing} onChange={setListing} />
          <div className="mt-3">
            <button
              onClick={handleSaveListing}
              disabled={saveStatus === "saving"}
              className="text-sm px-4 py-2 border rounded hover:bg-gray-50 transition-colors disabled:opacity-40"
            >
              {saveStatus === "saving"
                ? "Saving..."
                : saveStatus === "saved"
                  ? "Saved!"
                  : "Save to History"}
            </button>
          </div>
        </section>
      )}

      {/* Mockup Gallery */}
      {(mockupStatus === "generating" || mockups.length > 0) && (
        <section className="mb-6 sm:mb-8">
          <MockupGallery mockups={mockups} loading={mockupStatus === "generating"} />
        </section>
      )}

      {/* Publish to Etsy */}
      {listing && etsyStatus?.connected && (
        <section className="mb-6 sm:mb-8 p-4 sm:p-6 border rounded-lg bg-gray-50">
          <h2 className="text-base sm:text-lg font-semibold mb-4">Publish to Etsy</h2>

          <div className="flex items-center gap-3 sm:gap-4 mb-4">
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
              className="w-full sm:w-auto bg-orange-500 text-white px-6 py-3 rounded-lg font-medium hover:bg-orange-600 disabled:opacity-40 transition-colors"
            >
              Publish as Draft on Etsy
            </button>
          )}

          {publishStatus === "publishing" && (
            <div className="flex items-center gap-3">
              <div className="w-5 h-5 border-2 border-orange-500 border-t-transparent rounded-full animate-spin"></div>
              <span className="text-gray-600 text-sm">Publishing to Etsy...</span>
            </div>
          )}

          {publishStatus === "done" && publishResult && (
            <div className="p-3 sm:p-4 bg-green-50 border border-green-200 rounded">
              <p className="text-green-800 font-medium text-sm">Draft listing created!</p>
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
        <section className="mb-6 sm:mb-8 p-4 sm:p-6 border border-dashed border-orange-300 rounded-lg text-center">
          <p className="text-gray-600 mb-3 text-sm">Connect your Etsy shop to publish listings</p>
          <button
            onClick={handleConnectEtsy}
            className="px-5 py-2.5 bg-orange-500 text-white rounded-lg font-medium hover:bg-orange-600 transition-colors text-sm"
          >
            Connect Etsy
          </button>
        </section>
      )}

      {/* Listing History */}
      <section className="mb-6 sm:mb-8">
        <ListingHistory onLoad={handleLoadListing} refreshKey={historyRefreshKey} />
      </section>
    </main>
  );
}
