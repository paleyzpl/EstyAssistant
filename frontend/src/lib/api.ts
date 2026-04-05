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

export interface MockupImage {
  template_name: string;
  url: string;
}

export interface MockupResponse {
  mockups: MockupImage[];
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

export async function generateMockups(
  s3Key: string,
  templateNames?: string[]
): Promise<MockupResponse> {
  const res = await fetch(`${API_BASE}/mockups/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      s3_key: s3Key,
      template_names: templateNames,
    }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Mockup generation failed: ${detail}`);
  }
  return res.json();
}

// ── Etsy Auth ──

export interface AuthStatus {
  connected: boolean;
  shop_id: string | null;
}

export async function getEtsyAuthStatus(): Promise<AuthStatus> {
  const res = await fetch(`${API_BASE}/auth/etsy/status`);
  if (!res.ok) throw new Error("Failed to check Etsy status");
  return res.json();
}

export async function startEtsyAuth(): Promise<string> {
  const callbackUrl = `${window.location.origin}/auth/etsy/callback`;
  const res = await fetch(
    `${API_BASE}/auth/etsy/start?redirect_uri=${encodeURIComponent(callbackUrl)}`
  );
  if (!res.ok) throw new Error("Failed to start Etsy auth");
  const data = await res.json();
  return data.auth_url;
}

export async function completeEtsyAuth(
  code: string,
  state: string
): Promise<{ success: boolean; shop_id: string | null }> {
  const res = await fetch(
    `${API_BASE}/auth/etsy/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`,
    { method: "POST" }
  );
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Etsy auth failed: ${detail}`);
  }
  return res.json();
}

export async function disconnectEtsy(): Promise<void> {
  const res = await fetch(`${API_BASE}/auth/etsy/disconnect`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to disconnect Etsy");
}

// ── Publish ──

export interface PublishRequest {
  s3_key: string;
  sizes: string[];
  title: string;
  description: string;
  tags: string[];
  price: number;
}

export interface JobStatus {
  status: string;
  result?: {
    listing_id: string;
    listing_url: string | null;
    title: string;
  };
  error?: string;
}

export async function publishListing(
  req: PublishRequest
): Promise<string> {
  const res = await fetch(`${API_BASE}/publish`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Publish failed: ${detail}`);
  }
  const data = await res.json();
  return data.job_id;
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${API_BASE}/jobs/${jobId}`);
  if (!res.ok) throw new Error("Failed to get job status");
  return res.json();
}
