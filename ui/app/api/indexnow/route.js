/**
 * IndexNow API Route
 *
 * WHAT: Instantly notifies search engines when pages are added/updated
 * WHY: Get indexed in hours instead of days/weeks
 *
 * POST /api/indexnow
 * Body: { urls: string[] }
 *
 * Supported: Bing, Yandex, Seznam, Naver (Google uses different mechanism)
 */

import { NextResponse } from "next/server";

const INDEXNOW_KEY = process.env.INDEXNOW_KEY || "metricx-indexnow-key-2026";
const SITE_HOST = "www.metricx.ai";

/**
 * Submit URLs to IndexNow for instant indexing.
 */
export async function POST(request) {
  try {
    const { urls } = await request.json();

    if (!urls || !Array.isArray(urls) || urls.length === 0) {
      return NextResponse.json(
        { error: "urls array is required" },
        { status: 400 }
      );
    }

    // IndexNow API endpoint (Bing)
    const indexNowUrl = "https://api.indexnow.org/indexnow";

    const payload = {
      host: SITE_HOST,
      key: INDEXNOW_KEY,
      keyLocation: `https://${SITE_HOST}/${INDEXNOW_KEY}.txt`,
      urlList: urls.map((url) =>
        url.startsWith("http") ? url : `https://${SITE_HOST}${url}`
      ),
    };

    const response = await fetch(indexNowUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (response.ok || response.status === 202) {
      return NextResponse.json({
        success: true,
        submitted: urls.length,
        message: "URLs submitted to IndexNow successfully",
      });
    }

    const errorText = await response.text();
    return NextResponse.json(
      { error: "IndexNow submission failed", details: errorText },
      { status: response.status }
    );
  } catch (error) {
    console.error("IndexNow error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

/**
 * GET endpoint for health check and manual trigger.
 */
export async function GET() {
  return NextResponse.json({
    status: "ok",
    key: INDEXNOW_KEY,
    host: SITE_HOST,
    usage: "POST with { urls: string[] } to submit for indexing",
  });
}
