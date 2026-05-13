import { useState } from "react";

import { moduleShareCardUrl } from "../../api/modules";

/**
 * ShareCardActions — parent-shareable PNG card buttons.
 *
 * Renders a preview image (fetched from /api/modules/<id>/skill-report/card.png)
 * plus three actions: native share (WhatsApp on Android/iOS), direct download,
 * and copy link.
 */
export default function ShareCardActions({ moduleId }) {
  const [copied, setCopied] = useState(false);
  const cardUrl = `${window.location.origin}${moduleShareCardUrl(moduleId)}`;
  const caption =
    "I just finished the Mento Founder Lab — check out my skill card!";

  const shareNative = async () => {
    if (navigator.share) {
      try {
        const res = await fetch(cardUrl);
        const blob = await res.blob();
        const file = new File([blob], "mento-skill-card.png", { type: "image/png" });
        await navigator.share({ files: [file], text: caption });
        return;
      } catch (_) {
        // fall through to WhatsApp URL
      }
    }
    window.open(
      `https://wa.me/?text=${encodeURIComponent(caption + " " + cardUrl)}`,
      "_blank",
    );
  };

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(cardUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (_) {
      // clipboard may be blocked; fall back to a prompt
      window.prompt("Copy this link:", cardUrl);
    }
  };

  return (
    <section className="border-t pt-6">
      <h2 className="font-semibold mb-3">Share your skill card</h2>
      <img
        src={cardUrl}
        alt="Skill card preview"
        className="rounded-lg border shadow-sm max-w-xs"
      />
      <div className="flex gap-2 mt-3 flex-wrap">
        <button
          onClick={shareNative}
          className="bg-emerald-600 text-white rounded px-4 py-2 text-sm"
        >
          📲 Share to WhatsApp
        </button>
        <a
          href={cardUrl}
          download={`mento-skill-${moduleId}.png`}
          className="bg-slate-200 rounded px-4 py-2 text-sm"
        >
          ⬇️ Download PNG
        </a>
        <button
          onClick={copyLink}
          className="bg-slate-200 rounded px-4 py-2 text-sm"
        >
          {copied ? "✓ Copied" : "🔗 Copy link"}
        </button>
      </div>
    </section>
  );
}
