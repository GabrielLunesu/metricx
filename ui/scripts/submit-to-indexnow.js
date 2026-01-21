#!/usr/bin/env node
/**
 * Submit URLs to IndexNow for instant indexing
 *
 * WHAT: Submits all sitemap URLs to IndexNow API
 * WHY: Gets pages indexed in hours instead of weeks
 *
 * Usage: node scripts/submit-to-indexnow.js
 *
 * Related files:
 * - app/api/indexnow/route.js - IndexNow API endpoint
 * - public/metricx-indexnow-key-2024.txt - IndexNow key file
 */

const INDEXNOW_KEY = "metricx-indexnow-key-2024";
const SITE_HOST = "www.metricx.ai";
const INDEXNOW_URL = "https://api.indexnow.org/indexnow";

// Max URLs per submission (IndexNow limit is 10,000)
const BATCH_SIZE = 10000;

/**
 * Generate all URLs from the sitemap logic
 */
async function generateAllUrls() {
  const baseUrl = `https://${SITE_HOST}`;

  // Static pages
  const staticUrls = [
    baseUrl,
    `${baseUrl}/sign-in`,
    `${baseUrl}/sign-up`,
    `${baseUrl}/privacy`,
    `${baseUrl}/terms`,
  ];

  // Hub pages
  const hubUrls = [
    `${baseUrl}/glossary`,
    `${baseUrl}/vs`,
    `${baseUrl}/alternatives`,
    `${baseUrl}/tools`,
    `${baseUrl}/metrics`,
    `${baseUrl}/platforms`,
    `${baseUrl}/industries`,
    `${baseUrl}/integrations`,
    `${baseUrl}/use-cases`,
    `${baseUrl}/blog`,
  ];

  // Load content data
  const glossaryTerms = require("../content/glossary/terms.json");
  const competitors = require("../content/competitors/data.json");
  const metrics = require("../content/metrics/data.json");
  const platforms = require("../content/platforms/data.json");
  const industries = require("../content/industries/data.json");
  const integrations = require("../content/integrations/data.json");
  const useCases = require("../content/use-cases/data.json");
  const blogCategories = require("../content/blog/categories.json");

  const urls = [...staticUrls, ...hubUrls];

  // Glossary pages
  for (const term of glossaryTerms) {
    urls.push(`${baseUrl}/glossary/${term.slug}`);
  }

  // Competitor pages (vs and alternatives)
  for (const competitor of competitors) {
    urls.push(`${baseUrl}/vs/${competitor.slug}`);
    urls.push(`${baseUrl}/alternatives/${competitor.slug}`);
  }

  // Tool pages
  const tools = ["roas-calculator", "cpa-calculator", "cpm-calculator", "ctr-calculator", "ad-spend-calculator", "break-even-calculator"];
  for (const tool of tools) {
    urls.push(`${baseUrl}/tools/${tool}`);
  }

  // Metric pages
  for (const metric of metrics) {
    urls.push(`${baseUrl}/metrics/${metric.slug}`);
  }

  // Platform pages
  for (const platform of platforms) {
    urls.push(`${baseUrl}/platforms/${platform.slug}`);
  }

  // Industry pages
  for (const industry of industries) {
    urls.push(`${baseUrl}/industries/${industry.slug}`);
  }

  // Integration pages
  for (const integration of integrations) {
    urls.push(`${baseUrl}/integrations/${integration.slug}`);
  }

  // Use case pages
  for (const useCase of useCases) {
    urls.push(`${baseUrl}/use-cases/${useCase.slug}`);
  }

  // Blog category pages
  for (const category of blogCategories) {
    urls.push(`${baseUrl}/blog/${category.slug}`);
  }

  // Industry × Metric combination pages
  for (const industry of industries) {
    for (const metric of metrics) {
      urls.push(`${baseUrl}/industries/${industry.slug}/${metric.slug}`);
    }
  }

  // Platform × Metric combination pages
  for (const platform of platforms) {
    for (const metric of metrics) {
      urls.push(`${baseUrl}/platforms/${platform.slug}/${metric.slug}`);
    }
  }

  // Use Case × Industry combination pages
  for (const useCase of useCases) {
    for (const industry of industries) {
      urls.push(`${baseUrl}/use-cases/${useCase.slug}/${industry.slug}`);
    }
  }

  // Integration × Industry combination pages
  for (const integration of integrations) {
    for (const industry of industries) {
      urls.push(`${baseUrl}/integrations/${integration.slug}/${industry.slug}`);
    }
  }

  // Industry × Platform combination pages
  for (const industry of industries) {
    for (const platform of platforms) {
      urls.push(`${baseUrl}/industries/${industry.slug}/platforms/${platform.slug}`);
    }
  }

  return urls;
}

/**
 * Submit a batch of URLs to IndexNow
 */
async function submitBatch(urls, batchNumber) {
  const payload = {
    host: SITE_HOST,
    key: INDEXNOW_KEY,
    keyLocation: `https://${SITE_HOST}/${INDEXNOW_KEY}.txt`,
    urlList: urls,
  };

  console.log(`\nSubmitting batch ${batchNumber} (${urls.length} URLs)...`);

  try {
    const response = await fetch(INDEXNOW_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (response.ok || response.status === 202) {
      console.log(`✓ Batch ${batchNumber} submitted successfully (Status: ${response.status})`);
      return true;
    } else {
      const errorText = await response.text();
      console.error(`✗ Batch ${batchNumber} failed (Status: ${response.status}): ${errorText}`);
      return false;
    }
  } catch (error) {
    console.error(`✗ Batch ${batchNumber} error:`, error.message);
    return false;
  }
}

/**
 * Main function
 */
async function main() {
  console.log("=".repeat(60));
  console.log("IndexNow URL Submission Script");
  console.log("=".repeat(60));
  console.log(`Site: ${SITE_HOST}`);
  console.log(`Key: ${INDEXNOW_KEY}`);
  console.log("");

  // Generate all URLs
  console.log("Generating URL list...");
  const urls = await generateAllUrls();
  console.log(`Total URLs to submit: ${urls.length}`);

  // Split into batches
  const batches = [];
  for (let i = 0; i < urls.length; i += BATCH_SIZE) {
    batches.push(urls.slice(i, i + BATCH_SIZE));
  }
  console.log(`Batches to submit: ${batches.length}`);

  // Submit batches
  let successCount = 0;
  let failCount = 0;

  for (let i = 0; i < batches.length; i++) {
    const success = await submitBatch(batches[i], i + 1);
    if (success) {
      successCount++;
    } else {
      failCount++;
    }

    // Add delay between batches to avoid rate limiting
    if (i < batches.length - 1) {
      console.log("Waiting 2 seconds before next batch...");
      await new Promise((resolve) => setTimeout(resolve, 2000));
    }
  }

  // Summary
  console.log("\n" + "=".repeat(60));
  console.log("Submission Complete");
  console.log("=".repeat(60));
  console.log(`Total URLs: ${urls.length}`);
  console.log(`Successful batches: ${successCount}`);
  console.log(`Failed batches: ${failCount}`);

  if (failCount === 0) {
    console.log("\n✓ All URLs submitted to IndexNow successfully!");
    console.log("Pages should be indexed within 24-48 hours.");
  } else {
    console.log("\n⚠ Some batches failed. Check the errors above.");
  }
}

main().catch(console.error);
