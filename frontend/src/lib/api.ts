const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface UploadUrlResponse {
  upload_url: string;
  s3_key: string;
}

export interface ProcessedImage {
  size: string;
  download_url: string;
}

export interface ProcessResponse {
  preview_url: string;
  outputs: ProcessedImage[];
}

export interface ListingMetadata {
  title: string;
  tags: string[];
  description: string;
}

export async function getUploadUrl(
  contentType: string = "image/jpeg"
): Promise<UploadUrlResponse> {
  const res = await fetch(
    `${API_BASE}/upload-url?content_type=${encodeURIComponent(contentType)}`
  );
  if (!res.ok) throw new Error(`Failed to get upload URL: ${res.statusText}`);
  return res.json();
}

export async function uploadToS3(
  presignedUrl: string,
  file: File
): Promise<void> {
  const res = await fetch(presignedUrl, {
    method: "PUT",
    body: file,
    headers: { "Content-Type": file.type },
  });
  if (!res.ok) throw new Error(`S3 upload failed: ${res.statusText}`);
}

export async function processImage(
  s3Key: string,
  sizes: string[] = ["8x10"],
  skipSteps: string[] = []
): Promise<ProcessResponse> {
  const res = await fetch(`${API_BASE}/process`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      s3_key: s3Key,
      sizes,
      skip_steps: skipSteps,
    }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Processing failed: ${detail}`);
  }
  return res.json();
}

export async function generateListing(
  s3Key: string
): Promise<ListingMetadata> {
  const res = await fetch(`${API_BASE}/listing/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ s3_key: s3Key }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Listing generation failed: ${detail}`);
  }
  return res.json();
}
