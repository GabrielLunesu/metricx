/**
 * Campaign Detail Page - DEPRECATED
 * ==================================
 *
 * WHAT: Redirects to main campaigns page
 * WHY: Campaign details now shown in modal on the main campaigns page
 *
 * This page is kept for backwards compatibility with existing bookmarks/links.
 * The CampaignDetailModal on /campaigns now handles all campaign detail views.
 *
 * @deprecated Use CampaignDetailModal on /campaigns instead
 *
 * REFERENCES:
 *   - ui/app/(dashboard)/campaigns/page.jsx (new implementation)
 *   - ui/components/campaigns/CampaignDetailModal.jsx (detail modal)
 */
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";

export default function DeprecatedCampaignDetailPage() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to main campaigns page
    // TODO: Could pass campaign ID as query param to auto-open modal
    router.replace("/campaigns");
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <div className="text-center">
        <Loader2 className="w-8 h-8 animate-spin text-cyan-500 mx-auto mb-4" />
        <p className="text-slate-500 text-sm">Redirecting to campaigns...</p>
        <p className="text-slate-400 text-xs mt-2">
          Campaign details are now shown in a modal on the campaigns page.
        </p>
      </div>
    </div>
  );
}
