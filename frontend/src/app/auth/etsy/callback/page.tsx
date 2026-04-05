"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { completeEtsyAuth } from "@/lib/api";

function CallbackContent() {
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    const code = searchParams.get("code");
    const state = searchParams.get("state");

    if (!code || !state) {
      setStatus("error");
      setErrorMsg("Missing code or state parameter from Etsy.");
      return;
    }

    completeEtsyAuth(code, state)
      .then(() => {
        setStatus("success");
        setTimeout(() => {
          window.location.href = "/";
        }, 2000);
      })
      .catch((err) => {
        setStatus("error");
        setErrorMsg(err.message);
      });
  }, [searchParams]);

  return (
    <main className="max-w-md mx-auto px-4 py-16 text-center">
      {status === "loading" && (
        <div>
          <h1 className="text-2xl font-bold mb-4">Connecting to Etsy...</h1>
          <p className="text-gray-500">Exchanging authorization tokens.</p>
        </div>
      )}
      {status === "success" && (
        <div>
          <h1 className="text-2xl font-bold mb-4 text-green-700">Connected!</h1>
          <p className="text-gray-600">Your Etsy shop is now connected. Redirecting...</p>
        </div>
      )}
      {status === "error" && (
        <div>
          <h1 className="text-2xl font-bold mb-4 text-red-700">Connection Failed</h1>
          <p className="text-gray-600 mb-4">{errorMsg}</p>
          <a href="/" className="text-black underline">Back to home</a>
        </div>
      )}
    </main>
  );
}

export default function EtsyCallbackPage() {
  return (
    <Suspense fallback={
      <main className="max-w-md mx-auto px-4 py-16 text-center">
        <h1 className="text-2xl font-bold mb-4">Connecting to Etsy...</h1>
      </main>
    }>
      <CallbackContent />
    </Suspense>
  );
}
