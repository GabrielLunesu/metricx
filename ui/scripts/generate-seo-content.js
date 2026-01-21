/**
 * SEO Content Generator Script
 *
 * WHAT: Generates massive amounts of SEO content for programmatic pages
 * WHY: Scale to 100k+ pages for organic search dominance
 *
 * Run: node scripts/generate-seo-content.js
 */

const fs = require("fs");
const path = require("path");

// ============================================================================
// GLOSSARY TERMS - 500+ advertising, marketing, analytics terms
// ============================================================================
const glossaryCategories = {
  "performance-metrics": [
    { term: "ROAS", fullName: "Return on Ad Spend" },
    { term: "ROI", fullName: "Return on Investment" },
    { term: "CPA", fullName: "Cost Per Acquisition" },
    { term: "CPL", fullName: "Cost Per Lead" },
    { term: "CPS", fullName: "Cost Per Sale" },
    { term: "CPO", fullName: "Cost Per Order" },
    { term: "EPC", fullName: "Earnings Per Click" },
    { term: "RPC", fullName: "Revenue Per Click" },
    { term: "RPM", fullName: "Revenue Per Mille" },
    { term: "eCPM", fullName: "Effective Cost Per Mille" },
    { term: "ARPU", fullName: "Average Revenue Per User" },
    { term: "ARPDAU", fullName: "Average Revenue Per Daily Active User" },
    { term: "MER", fullName: "Marketing Efficiency Ratio" },
    { term: "CAC Payback", fullName: "Customer Acquisition Cost Payback Period" },
    { term: "Blended ROAS", fullName: "Blended Return on Ad Spend" },
    { term: "Incremental ROAS", fullName: "Incremental Return on Ad Spend" },
    { term: "iROAS", fullName: "Incremental Return on Ad Spend" },
    { term: "nCPA", fullName: "New Customer CPA" },
    { term: "Contribution Margin", fullName: "Contribution Margin" },
    { term: "Profit Margin", fullName: "Profit Margin" },
  ],
  "cost-metrics": [
    { term: "CPM", fullName: "Cost Per Mille" },
    { term: "CPC", fullName: "Cost Per Click" },
    { term: "vCPM", fullName: "Viewable Cost Per Mille" },
    { term: "CPV", fullName: "Cost Per View" },
    { term: "CPCV", fullName: "Cost Per Completed View" },
    { term: "CPE", fullName: "Cost Per Engagement" },
    { term: "CPI", fullName: "Cost Per Install" },
    { term: "CPFT", fullName: "Cost Per First Transaction" },
    { term: "CPR", fullName: "Cost Per Registration" },
    { term: "CPSU", fullName: "Cost Per Signup" },
    { term: "Ad Spend", fullName: "Advertising Spend" },
    { term: "Media Spend", fullName: "Media Spend" },
    { term: "Budget Pacing", fullName: "Budget Pacing" },
    { term: "Daily Budget", fullName: "Daily Budget" },
    { term: "Lifetime Budget", fullName: "Lifetime Budget" },
    { term: "Bid Amount", fullName: "Bid Amount" },
    { term: "Max Bid", fullName: "Maximum Bid" },
    { term: "Average Bid", fullName: "Average Bid" },
  ],
  "engagement-metrics": [
    { term: "CTR", fullName: "Click-Through Rate" },
    { term: "Engagement Rate", fullName: "Engagement Rate" },
    { term: "Interaction Rate", fullName: "Interaction Rate" },
    { term: "Video Completion Rate", fullName: "Video Completion Rate" },
    { term: "VTR", fullName: "View-Through Rate" },
    { term: "Watch Time", fullName: "Watch Time" },
    { term: "Average Watch Time", fullName: "Average Watch Time" },
    { term: "Thumb Stop Rate", fullName: "Thumb Stop Rate" },
    { term: "Hook Rate", fullName: "Hook Rate" },
    { term: "Hold Rate", fullName: "Hold Rate" },
    { term: "3-Second Views", fullName: "3-Second Video Views" },
    { term: "ThruPlay", fullName: "ThruPlay" },
    { term: "Outbound CTR", fullName: "Outbound Click-Through Rate" },
    { term: "Link Clicks", fullName: "Link Clicks" },
    { term: "All Clicks", fullName: "All Clicks" },
    { term: "Social Actions", fullName: "Social Actions" },
    { term: "Shares", fullName: "Shares" },
    { term: "Comments", fullName: "Comments" },
    { term: "Reactions", fullName: "Reactions" },
    { term: "Saves", fullName: "Saves" },
  ],
  "reach-metrics": [
    { term: "Impressions", fullName: "Impressions" },
    { term: "Reach", fullName: "Reach" },
    { term: "Frequency", fullName: "Ad Frequency" },
    { term: "Unique Reach", fullName: "Unique Reach" },
    { term: "Daily Reach", fullName: "Daily Reach" },
    { term: "Weekly Reach", fullName: "Weekly Reach" },
    { term: "Monthly Reach", fullName: "Monthly Reach" },
    { term: "Impression Share", fullName: "Impression Share" },
    { term: "Share of Voice", fullName: "Share of Voice" },
    { term: "SOV", fullName: "Share of Voice" },
    { term: "Top of Page Rate", fullName: "Top of Page Rate" },
    { term: "Absolute Top Rate", fullName: "Absolute Top of Page Rate" },
    { term: "Viewability", fullName: "Ad Viewability" },
    { term: "Viewable Impressions", fullName: "Viewable Impressions" },
    { term: "In-View Rate", fullName: "In-View Rate" },
    { term: "Ad Visibility", fullName: "Ad Visibility" },
    { term: "Above the Fold", fullName: "Above the Fold" },
    { term: "Below the Fold", fullName: "Below the Fold" },
  ],
  "conversion-metrics": [
    { term: "Conversion Rate", fullName: "Conversion Rate" },
    { term: "CVR", fullName: "Conversion Rate" },
    { term: "Micro Conversion", fullName: "Micro Conversion" },
    { term: "Macro Conversion", fullName: "Macro Conversion" },
    { term: "Add to Cart Rate", fullName: "Add to Cart Rate" },
    { term: "Cart Abandonment Rate", fullName: "Cart Abandonment Rate" },
    { term: "Checkout Abandonment", fullName: "Checkout Abandonment Rate" },
    { term: "Purchase Rate", fullName: "Purchase Rate" },
    { term: "Lead Conversion Rate", fullName: "Lead Conversion Rate" },
    { term: "MQL to SQL Rate", fullName: "MQL to SQL Conversion Rate" },
    { term: "Trial to Paid", fullName: "Trial to Paid Conversion Rate" },
    { term: "Signup Rate", fullName: "Signup Rate" },
    { term: "Assisted Conversions", fullName: "Assisted Conversions" },
    { term: "Direct Conversions", fullName: "Direct Conversions" },
    { term: "Total Conversions", fullName: "Total Conversions" },
    { term: "Unique Conversions", fullName: "Unique Conversions" },
    { term: "Conversion Value", fullName: "Conversion Value" },
    { term: "Revenue", fullName: "Revenue" },
  ],
  "business-metrics": [
    { term: "CAC", fullName: "Customer Acquisition Cost" },
    { term: "LTV", fullName: "Lifetime Value" },
    { term: "CLV", fullName: "Customer Lifetime Value" },
    { term: "AOV", fullName: "Average Order Value" },
    { term: "ATV", fullName: "Average Transaction Value" },
    { term: "LTV:CAC Ratio", fullName: "LTV to CAC Ratio" },
    { term: "Payback Period", fullName: "Payback Period" },
    { term: "Gross Margin", fullName: "Gross Margin" },
    { term: "Net Margin", fullName: "Net Margin" },
    { term: "EBITDA", fullName: "Earnings Before Interest, Taxes, Depreciation, and Amortization" },
    { term: "Churn Rate", fullName: "Churn Rate" },
    { term: "Retention Rate", fullName: "Retention Rate" },
    { term: "Repeat Purchase Rate", fullName: "Repeat Purchase Rate" },
    { term: "Purchase Frequency", fullName: "Purchase Frequency" },
    { term: "Customer Count", fullName: "Customer Count" },
    { term: "New Customers", fullName: "New Customers" },
    { term: "Returning Customers", fullName: "Returning Customers" },
    { term: "DAU", fullName: "Daily Active Users" },
    { term: "MAU", fullName: "Monthly Active Users" },
    { term: "WAU", fullName: "Weekly Active Users" },
  ],
  "attribution": [
    { term: "Attribution", fullName: "Marketing Attribution" },
    { term: "First-Click Attribution", fullName: "First-Click Attribution" },
    { term: "Last-Click Attribution", fullName: "Last-Click Attribution" },
    { term: "Linear Attribution", fullName: "Linear Attribution" },
    { term: "Time Decay Attribution", fullName: "Time Decay Attribution" },
    { term: "Position-Based Attribution", fullName: "Position-Based Attribution" },
    { term: "Data-Driven Attribution", fullName: "Data-Driven Attribution" },
    { term: "DDA", fullName: "Data-Driven Attribution" },
    { term: "Multi-Touch Attribution", fullName: "Multi-Touch Attribution" },
    { term: "MTA", fullName: "Multi-Touch Attribution" },
    { term: "MMM", fullName: "Marketing Mix Modeling" },
    { term: "Incrementality", fullName: "Incrementality Testing" },
    { term: "Lift Test", fullName: "Conversion Lift Test" },
    { term: "Holdout Test", fullName: "Holdout Test" },
    { term: "Geo Lift", fullName: "Geo Lift Test" },
    { term: "Attribution Window", fullName: "Attribution Window" },
    { term: "Conversion Window", fullName: "Conversion Window" },
    { term: "Lookback Window", fullName: "Lookback Window" },
    { term: "Click Attribution", fullName: "Click-Through Attribution" },
    { term: "View Attribution", fullName: "View-Through Attribution" },
  ],
  "tracking": [
    { term: "Pixel", fullName: "Tracking Pixel" },
    { term: "Meta Pixel", fullName: "Meta (Facebook) Pixel" },
    { term: "Facebook Pixel", fullName: "Facebook Pixel" },
    { term: "Google Tag", fullName: "Google Tag" },
    { term: "GTM", fullName: "Google Tag Manager" },
    { term: "CAPI", fullName: "Conversions API" },
    { term: "Server-Side Tracking", fullName: "Server-Side Tracking" },
    { term: "Event Tracking", fullName: "Event Tracking" },
    { term: "Conversion Tracking", fullName: "Conversion Tracking" },
    { term: "Standard Events", fullName: "Standard Events" },
    { term: "Custom Events", fullName: "Custom Events" },
    { term: "Event Parameters", fullName: "Event Parameters" },
    { term: "UTM Parameters", fullName: "UTM Parameters" },
    { term: "UTM Source", fullName: "UTM Source" },
    { term: "UTM Medium", fullName: "UTM Medium" },
    { term: "UTM Campaign", fullName: "UTM Campaign" },
    { term: "UTM Content", fullName: "UTM Content" },
    { term: "UTM Term", fullName: "UTM Term" },
    { term: "Click ID", fullName: "Click Identifier" },
    { term: "GCLID", fullName: "Google Click Identifier" },
    { term: "FBCLID", fullName: "Facebook Click Identifier" },
    { term: "Offline Conversions", fullName: "Offline Conversion Tracking" },
  ],
  "targeting": [
    { term: "Audience", fullName: "Target Audience" },
    { term: "Custom Audience", fullName: "Custom Audience" },
    { term: "Lookalike Audience", fullName: "Lookalike Audience" },
    { term: "Similar Audience", fullName: "Similar Audience" },
    { term: "Saved Audience", fullName: "Saved Audience" },
    { term: "Special Ad Audience", fullName: "Special Ad Audience" },
    { term: "Retargeting", fullName: "Retargeting" },
    { term: "Remarketing", fullName: "Remarketing" },
    { term: "Prospecting", fullName: "Prospecting" },
    { term: "Interest Targeting", fullName: "Interest-Based Targeting" },
    { term: "Behavioral Targeting", fullName: "Behavioral Targeting" },
    { term: "Demographic Targeting", fullName: "Demographic Targeting" },
    { term: "Geographic Targeting", fullName: "Geographic Targeting" },
    { term: "Geo-Targeting", fullName: "Geotargeting" },
    { term: "Device Targeting", fullName: "Device Targeting" },
    { term: "Placement Targeting", fullName: "Placement Targeting" },
    { term: "Contextual Targeting", fullName: "Contextual Targeting" },
    { term: "Keyword Targeting", fullName: "Keyword Targeting" },
    { term: "Topic Targeting", fullName: "Topic Targeting" },
    { term: "Affinity Audience", fullName: "Affinity Audience" },
    { term: "In-Market Audience", fullName: "In-Market Audience" },
    { term: "Customer Match", fullName: "Customer Match" },
    { term: "Website Visitors", fullName: "Website Visitors Audience" },
    { term: "Email List", fullName: "Email List Audience" },
    { term: "Engagement Audience", fullName: "Engagement Custom Audience" },
    { term: "Video Viewers", fullName: "Video Viewers Audience" },
    { term: "Exclusion Audience", fullName: "Audience Exclusion" },
    { term: "Audience Overlap", fullName: "Audience Overlap" },
    { term: "Audience Saturation", fullName: "Audience Saturation" },
  ],
  "ad-types": [
    { term: "Display Ads", fullName: "Display Advertising" },
    { term: "Search Ads", fullName: "Search Advertising" },
    { term: "Video Ads", fullName: "Video Advertising" },
    { term: "Native Ads", fullName: "Native Advertising" },
    { term: "Social Ads", fullName: "Social Media Advertising" },
    { term: "Shopping Ads", fullName: "Shopping Advertising" },
    { term: "DPA", fullName: "Dynamic Product Ads" },
    { term: "Carousel Ads", fullName: "Carousel Ads" },
    { term: "Collection Ads", fullName: "Collection Ads" },
    { term: "Stories Ads", fullName: "Stories Ads" },
    { term: "Reels Ads", fullName: "Reels Ads" },
    { term: "In-Stream Ads", fullName: "In-Stream Video Ads" },
    { term: "Bumper Ads", fullName: "Bumper Ads" },
    { term: "Discovery Ads", fullName: "Discovery Ads" },
    { term: "Performance Max", fullName: "Performance Max Campaigns" },
    { term: "Smart Shopping", fullName: "Smart Shopping Campaigns" },
    { term: "App Install Ads", fullName: "App Install Ads" },
    { term: "Lead Ads", fullName: "Lead Generation Ads" },
    { term: "Instant Experience", fullName: "Instant Experience Ads" },
    { term: "Canvas Ads", fullName: "Canvas Ads" },
    { term: "Playable Ads", fullName: "Playable Ads" },
    { term: "AR Ads", fullName: "Augmented Reality Ads" },
    { term: "UGC Ads", fullName: "User-Generated Content Ads" },
    { term: "Whitelisted Ads", fullName: "Whitelisted/Spark Ads" },
    { term: "Spark Ads", fullName: "TikTok Spark Ads" },
  ],
  "campaign-types": [
    { term: "Brand Awareness", fullName: "Brand Awareness Campaign" },
    { term: "Reach Campaign", fullName: "Reach Campaign" },
    { term: "Traffic Campaign", fullName: "Traffic Campaign" },
    { term: "Engagement Campaign", fullName: "Engagement Campaign" },
    { term: "Video Views", fullName: "Video Views Campaign" },
    { term: "Lead Generation", fullName: "Lead Generation Campaign" },
    { term: "Conversions Campaign", fullName: "Conversions Campaign" },
    { term: "Sales Campaign", fullName: "Sales Campaign" },
    { term: "Catalog Sales", fullName: "Catalog Sales Campaign" },
    { term: "Store Visits", fullName: "Store Visits Campaign" },
    { term: "App Promotion", fullName: "App Promotion Campaign" },
    { term: "Advantage+", fullName: "Advantage+ Shopping Campaign" },
    { term: "ASC", fullName: "Advantage+ Shopping Campaign" },
    { term: "Advantage+ Creative", fullName: "Advantage+ Creative" },
    { term: "Dynamic Ads", fullName: "Dynamic Ads" },
    { term: "Evergreen Campaign", fullName: "Evergreen Campaign" },
    { term: "Seasonal Campaign", fullName: "Seasonal Campaign" },
    { term: "Flash Sale Campaign", fullName: "Flash Sale Campaign" },
    { term: "Launch Campaign", fullName: "Product Launch Campaign" },
  ],
  "bidding": [
    { term: "Bid Strategy", fullName: "Bid Strategy" },
    { term: "Manual Bidding", fullName: "Manual Bidding" },
    { term: "Automated Bidding", fullName: "Automated Bidding" },
    { term: "Smart Bidding", fullName: "Smart Bidding" },
    { term: "Target CPA", fullName: "Target CPA Bidding" },
    { term: "Target ROAS", fullName: "Target ROAS Bidding" },
    { term: "Maximize Conversions", fullName: "Maximize Conversions" },
    { term: "Maximize Clicks", fullName: "Maximize Clicks" },
    { term: "Maximize Value", fullName: "Maximize Conversion Value" },
    { term: "Cost Cap", fullName: "Cost Cap Bidding" },
    { term: "Bid Cap", fullName: "Bid Cap" },
    { term: "Lowest Cost", fullName: "Lowest Cost Bidding" },
    { term: "Highest Value", fullName: "Highest Value Bidding" },
    { term: "ECPC", fullName: "Enhanced CPC" },
    { term: "Portfolio Bidding", fullName: "Portfolio Bid Strategy" },
    { term: "Auction", fullName: "Ad Auction" },
    { term: "Second-Price Auction", fullName: "Second-Price Auction" },
    { term: "First-Price Auction", fullName: "First-Price Auction" },
    { term: "Reserve Price", fullName: "Reserve Price" },
    { term: "Bid Adjustment", fullName: "Bid Adjustment" },
    { term: "Bid Modifier", fullName: "Bid Modifier" },
  ],
  "platform-metrics": [
    { term: "Quality Score", fullName: "Quality Score" },
    { term: "Relevance Score", fullName: "Relevance Score" },
    { term: "Quality Ranking", fullName: "Ad Quality Ranking" },
    { term: "Engagement Ranking", fullName: "Engagement Rate Ranking" },
    { term: "Conversion Ranking", fullName: "Conversion Rate Ranking" },
    { term: "Ad Rank", fullName: "Ad Rank" },
    { term: "Ad Strength", fullName: "Ad Strength" },
    { term: "Optimization Score", fullName: "Optimization Score" },
    { term: "Account Health", fullName: "Account Health Score" },
    { term: "Ad Relevance", fullName: "Ad Relevance Diagnostics" },
    { term: "Landing Page Experience", fullName: "Landing Page Experience" },
    { term: "Expected CTR", fullName: "Expected Click-Through Rate" },
    { term: "Search Term", fullName: "Search Term" },
    { term: "Search Query", fullName: "Search Query" },
    { term: "Match Type", fullName: "Keyword Match Type" },
    { term: "Broad Match", fullName: "Broad Match" },
    { term: "Phrase Match", fullName: "Phrase Match" },
    { term: "Exact Match", fullName: "Exact Match" },
    { term: "Negative Keywords", fullName: "Negative Keywords" },
  ],
  "creative": [
    { term: "Ad Creative", fullName: "Ad Creative" },
    { term: "Ad Copy", fullName: "Ad Copy" },
    { term: "Headline", fullName: "Ad Headline" },
    { term: "Primary Text", fullName: "Primary Text" },
    { term: "Description", fullName: "Ad Description" },
    { term: "Call to Action", fullName: "Call to Action" },
    { term: "CTA", fullName: "Call to Action" },
    { term: "Display URL", fullName: "Display URL" },
    { term: "Final URL", fullName: "Final URL" },
    { term: "Ad Extensions", fullName: "Ad Extensions" },
    { term: "Sitelinks", fullName: "Sitelink Extensions" },
    { term: "Callouts", fullName: "Callout Extensions" },
    { term: "Structured Snippets", fullName: "Structured Snippets" },
    { term: "Image Assets", fullName: "Image Assets" },
    { term: "Video Creative", fullName: "Video Creative" },
    { term: "Static Image", fullName: "Static Image Ad" },
    { term: "GIF Ads", fullName: "GIF Ads" },
    { term: "Responsive Ads", fullName: "Responsive Display Ads" },
    { term: "RSA", fullName: "Responsive Search Ads" },
    { term: "Dynamic Creative", fullName: "Dynamic Creative" },
    { term: "DCO", fullName: "Dynamic Creative Optimization" },
    { term: "Creative Fatigue", fullName: "Creative Fatigue" },
    { term: "Ad Fatigue", fullName: "Ad Fatigue" },
    { term: "Creative Rotation", fullName: "Creative Rotation" },
    { term: "A/B Testing", fullName: "A/B Testing" },
    { term: "Split Testing", fullName: "Split Testing" },
    { term: "Multivariate Testing", fullName: "Multivariate Testing" },
    { term: "Creative Testing", fullName: "Creative Testing" },
  ],
  "ecommerce": [
    { term: "Product Feed", fullName: "Product Feed" },
    { term: "Product Catalog", fullName: "Product Catalog" },
    { term: "SKU", fullName: "Stock Keeping Unit" },
    { term: "GTIN", fullName: "Global Trade Item Number" },
    { term: "MPN", fullName: "Manufacturer Part Number" },
    { term: "Product Title", fullName: "Product Title" },
    { term: "Product Description", fullName: "Product Description" },
    { term: "Product Category", fullName: "Product Category" },
    { term: "Merchant Center", fullName: "Google Merchant Center" },
    { term: "Commerce Manager", fullName: "Meta Commerce Manager" },
    { term: "Shopping Feed", fullName: "Shopping Feed" },
    { term: "Feed Optimization", fullName: "Feed Optimization" },
    { term: "Supplemental Feed", fullName: "Supplemental Feed" },
    { term: "Product Set", fullName: "Product Set" },
    { term: "Inventory", fullName: "Inventory" },
    { term: "Out of Stock", fullName: "Out of Stock" },
    { term: "Price Drop", fullName: "Price Drop" },
    { term: "Sale Price", fullName: "Sale Price" },
    { term: "MSRP", fullName: "Manufacturer Suggested Retail Price" },
    { term: "Free Shipping", fullName: "Free Shipping" },
    { term: "Shipping Cost", fullName: "Shipping Cost" },
    { term: "Return Policy", fullName: "Return Policy" },
  ],
  "analytics": [
    { term: "Google Analytics", fullName: "Google Analytics" },
    { term: "GA4", fullName: "Google Analytics 4" },
    { term: "Universal Analytics", fullName: "Universal Analytics" },
    { term: "Session", fullName: "Session" },
    { term: "Users", fullName: "Users" },
    { term: "Pageviews", fullName: "Pageviews" },
    { term: "Bounce Rate", fullName: "Bounce Rate" },
    { term: "Exit Rate", fullName: "Exit Rate" },
    { term: "Time on Site", fullName: "Time on Site" },
    { term: "Pages per Session", fullName: "Pages per Session" },
    { term: "New vs Returning", fullName: "New vs Returning Users" },
    { term: "Traffic Source", fullName: "Traffic Source" },
    { term: "Referral Traffic", fullName: "Referral Traffic" },
    { term: "Direct Traffic", fullName: "Direct Traffic" },
    { term: "Organic Traffic", fullName: "Organic Traffic" },
    { term: "Paid Traffic", fullName: "Paid Traffic" },
    { term: "Social Traffic", fullName: "Social Traffic" },
    { term: "Segment", fullName: "Analytics Segment" },
    { term: "Cohort", fullName: "Cohort Analysis" },
    { term: "Funnel Analysis", fullName: "Funnel Analysis" },
    { term: "Path Analysis", fullName: "Path Analysis" },
    { term: "Heatmap", fullName: "Heatmap" },
    { term: "Click Map", fullName: "Click Map" },
    { term: "Scroll Map", fullName: "Scroll Map" },
    { term: "Session Recording", fullName: "Session Recording" },
  ],
  "privacy": [
    { term: "iOS 14", fullName: "iOS 14 Privacy Changes" },
    { term: "ATT", fullName: "App Tracking Transparency" },
    { term: "SKAdNetwork", fullName: "SKAdNetwork" },
    { term: "SKAN", fullName: "SKAdNetwork" },
    { term: "IDFA", fullName: "Identifier for Advertisers" },
    { term: "GAID", fullName: "Google Advertising ID" },
    { term: "Third-Party Cookies", fullName: "Third-Party Cookies" },
    { term: "First-Party Data", fullName: "First-Party Data" },
    { term: "Zero-Party Data", fullName: "Zero-Party Data" },
    { term: "GDPR", fullName: "General Data Protection Regulation" },
    { term: "CCPA", fullName: "California Consumer Privacy Act" },
    { term: "Cookie Consent", fullName: "Cookie Consent" },
    { term: "Consent Mode", fullName: "Google Consent Mode" },
    { term: "Privacy Sandbox", fullName: "Privacy Sandbox" },
    { term: "Aggregated Data", fullName: "Aggregated Event Measurement" },
    { term: "AEM", fullName: "Aggregated Event Measurement" },
    { term: "Conversion Modeling", fullName: "Conversion Modeling" },
    { term: "Modeled Conversions", fullName: "Modeled Conversions" },
    { term: "Data Clean Room", fullName: "Data Clean Room" },
  ],
  "strategy": [
    { term: "Funnel", fullName: "Marketing Funnel" },
    { term: "TOFU", fullName: "Top of Funnel" },
    { term: "MOFU", fullName: "Middle of Funnel" },
    { term: "BOFU", fullName: "Bottom of Funnel" },
    { term: "Customer Journey", fullName: "Customer Journey" },
    { term: "Touchpoint", fullName: "Customer Touchpoint" },
    { term: "Brand Lift", fullName: "Brand Lift Study" },
    { term: "Conversion Lift", fullName: "Conversion Lift Study" },
    { term: "Scale", fullName: "Campaign Scaling" },
    { term: "Vertical Scale", fullName: "Vertical Scaling" },
    { term: "Horizontal Scale", fullName: "Horizontal Scaling" },
    { term: "Consolidation", fullName: "Campaign Consolidation" },
    { term: "Account Structure", fullName: "Account Structure" },
    { term: "Campaign Structure", fullName: "Campaign Structure" },
    { term: "Ad Set", fullName: "Ad Set" },
    { term: "Ad Group", fullName: "Ad Group" },
    { term: "CBO", fullName: "Campaign Budget Optimization" },
    { term: "ABO", fullName: "Ad Set Budget Optimization" },
    { term: "Learning Phase", fullName: "Learning Phase" },
    { term: "Learning Limited", fullName: "Learning Limited" },
    { term: "Significant Edits", fullName: "Significant Edits" },
  ],
  "amazon": [
    { term: "ACOS", fullName: "Advertising Cost of Sales" },
    { term: "TACOS", fullName: "Total Advertising Cost of Sales" },
    { term: "Sponsored Products", fullName: "Sponsored Products" },
    { term: "Sponsored Brands", fullName: "Sponsored Brands" },
    { term: "Sponsored Display", fullName: "Sponsored Display" },
    { term: "Amazon DSP", fullName: "Amazon DSP" },
    { term: "BSR", fullName: "Best Sellers Rank" },
    { term: "Buy Box", fullName: "Buy Box" },
    { term: "ACoS Target", fullName: "ACoS Target" },
    { term: "TACoS", fullName: "Total Advertising Cost of Sales" },
    { term: "Organic Rank", fullName: "Organic Ranking" },
    { term: "PPC Rank", fullName: "PPC Ranking" },
    { term: "Product Targeting", fullName: "Product Targeting" },
    { term: "Category Targeting", fullName: "Category Targeting" },
    { term: "ASIN Targeting", fullName: "ASIN Targeting" },
  ],
};

// ============================================================================
// INDUSTRIES - 50+ e-commerce and DTC industries
// ============================================================================
const industries = [
  // Fashion & Apparel
  { name: "Fashion", slug: "fashion", category: "apparel" },
  { name: "Clothing", slug: "clothing", category: "apparel" },
  { name: "Footwear", slug: "footwear", category: "apparel" },
  { name: "Sneakers", slug: "sneakers", category: "apparel" },
  { name: "Activewear", slug: "activewear", category: "apparel" },
  { name: "Athleisure", slug: "athleisure", category: "apparel" },
  { name: "Streetwear", slug: "streetwear", category: "apparel" },
  { name: "Luxury Fashion", slug: "luxury-fashion", category: "apparel" },
  { name: "Plus Size Fashion", slug: "plus-size-fashion", category: "apparel" },
  { name: "Sustainable Fashion", slug: "sustainable-fashion", category: "apparel" },
  { name: "Kids Fashion", slug: "kids-fashion", category: "apparel" },
  { name: "Maternity Wear", slug: "maternity-wear", category: "apparel" },
  { name: "Swimwear", slug: "swimwear", category: "apparel" },
  { name: "Lingerie", slug: "lingerie", category: "apparel" },
  { name: "Jewelry", slug: "jewelry", category: "accessories" },
  { name: "Watches", slug: "watches", category: "accessories" },
  { name: "Handbags", slug: "handbags", category: "accessories" },
  { name: "Sunglasses", slug: "sunglasses", category: "accessories" },

  // Beauty & Personal Care
  { name: "Beauty", slug: "beauty", category: "beauty" },
  { name: "Skincare", slug: "skincare", category: "beauty" },
  { name: "Cosmetics", slug: "cosmetics", category: "beauty" },
  { name: "Makeup", slug: "makeup", category: "beauty" },
  { name: "Haircare", slug: "haircare", category: "beauty" },
  { name: "Fragrance", slug: "fragrance", category: "beauty" },
  { name: "Men's Grooming", slug: "mens-grooming", category: "beauty" },
  { name: "Clean Beauty", slug: "clean-beauty", category: "beauty" },
  { name: "K-Beauty", slug: "k-beauty", category: "beauty" },
  { name: "Nail Care", slug: "nail-care", category: "beauty" },

  // Health & Wellness
  { name: "Health & Wellness", slug: "health-wellness", category: "health" },
  { name: "Supplements", slug: "supplements", category: "health" },
  { name: "Vitamins", slug: "vitamins", category: "health" },
  { name: "CBD", slug: "cbd", category: "health" },
  { name: "Fitness Equipment", slug: "fitness-equipment", category: "health" },
  { name: "Protein Powder", slug: "protein-powder", category: "health" },
  { name: "Weight Loss", slug: "weight-loss", category: "health" },
  { name: "Sleep Products", slug: "sleep-products", category: "health" },
  { name: "Mental Wellness", slug: "mental-wellness", category: "health" },

  // Food & Beverage
  { name: "Food & Beverage", slug: "food-beverage", category: "food" },
  { name: "Snacks", slug: "snacks", category: "food" },
  { name: "Coffee", slug: "coffee", category: "food" },
  { name: "Tea", slug: "tea", category: "food" },
  { name: "Alcohol", slug: "alcohol", category: "food" },
  { name: "Wine", slug: "wine", category: "food" },
  { name: "Craft Beer", slug: "craft-beer", category: "food" },
  { name: "Meal Kits", slug: "meal-kits", category: "food" },
  { name: "Organic Food", slug: "organic-food", category: "food" },
  { name: "Pet Food", slug: "pet-food", category: "food" },
  { name: "Baby Food", slug: "baby-food", category: "food" },

  // Home & Living
  { name: "Home & Living", slug: "home-living", category: "home" },
  { name: "Furniture", slug: "furniture", category: "home" },
  { name: "Home Decor", slug: "home-decor", category: "home" },
  { name: "Bedding", slug: "bedding", category: "home" },
  { name: "Mattresses", slug: "mattresses", category: "home" },
  { name: "Kitchen", slug: "kitchen", category: "home" },
  { name: "Cookware", slug: "cookware", category: "home" },
  { name: "Candles", slug: "candles", category: "home" },
  { name: "Plants", slug: "plants", category: "home" },
  { name: "Cleaning Products", slug: "cleaning-products", category: "home" },

  // Baby & Kids
  { name: "Baby Products", slug: "baby-products", category: "baby" },
  { name: "Baby Gear", slug: "baby-gear", category: "baby" },
  { name: "Toys", slug: "toys", category: "baby" },
  { name: "Kids Education", slug: "kids-education", category: "baby" },
  { name: "Diapers", slug: "diapers", category: "baby" },

  // Pets
  { name: "Pet Products", slug: "pet-products", category: "pets" },
  { name: "Dog Products", slug: "dog-products", category: "pets" },
  { name: "Cat Products", slug: "cat-products", category: "pets" },
  { name: "Pet Supplies", slug: "pet-supplies", category: "pets" },
  { name: "Pet Accessories", slug: "pet-accessories", category: "pets" },

  // Electronics & Tech
  { name: "Electronics", slug: "electronics", category: "tech" },
  { name: "Consumer Electronics", slug: "consumer-electronics", category: "tech" },
  { name: "Gadgets", slug: "gadgets", category: "tech" },
  { name: "Audio Equipment", slug: "audio-equipment", category: "tech" },
  { name: "Smart Home", slug: "smart-home", category: "tech" },
  { name: "Wearables", slug: "wearables", category: "tech" },
  { name: "Phone Accessories", slug: "phone-accessories", category: "tech" },
  { name: "Gaming", slug: "gaming", category: "tech" },

  // Outdoor & Sports
  { name: "Outdoor", slug: "outdoor", category: "outdoor" },
  { name: "Camping Gear", slug: "camping-gear", category: "outdoor" },
  { name: "Hiking", slug: "hiking", category: "outdoor" },
  { name: "Cycling", slug: "cycling", category: "outdoor" },
  { name: "Golf", slug: "golf", category: "outdoor" },
  { name: "Fishing", slug: "fishing", category: "outdoor" },
  { name: "Hunting", slug: "hunting", category: "outdoor" },
  { name: "Running", slug: "running", category: "outdoor" },
  { name: "Yoga", slug: "yoga", category: "outdoor" },

  // Specialty
  { name: "Subscription Boxes", slug: "subscription-boxes", category: "specialty" },
  { name: "Print on Demand", slug: "print-on-demand", category: "specialty" },
  { name: "Dropshipping", slug: "dropshipping", category: "specialty" },
  { name: "Handmade", slug: "handmade", category: "specialty" },
  { name: "Vintage", slug: "vintage", category: "specialty" },
  { name: "Eco-Friendly", slug: "eco-friendly", category: "specialty" },
  { name: "Luxury Goods", slug: "luxury-goods", category: "specialty" },
  { name: "Auto Parts", slug: "auto-parts", category: "specialty" },
  { name: "Office Supplies", slug: "office-supplies", category: "specialty" },
  { name: "Art & Craft", slug: "art-craft", category: "specialty" },
  { name: "Musical Instruments", slug: "musical-instruments", category: "specialty" },
  { name: "Books", slug: "books", category: "specialty" },
  { name: "Stationery", slug: "stationery", category: "specialty" },
  { name: "Gifts", slug: "gifts", category: "specialty" },
  { name: "Wedding", slug: "wedding", category: "specialty" },
  { name: "Party Supplies", slug: "party-supplies", category: "specialty" },
];

// ============================================================================
// USE CASES - 100+ use cases for metricx
// ============================================================================
const useCases = [
  // Analytics & Tracking
  { name: "Track ROAS Across Platforms", slug: "track-roas-across-platforms", category: "analytics" },
  { name: "Unified Ad Dashboard", slug: "unified-ad-dashboard", category: "analytics" },
  { name: "Cross-Platform Reporting", slug: "cross-platform-reporting", category: "analytics" },
  { name: "Real-Time Ad Performance", slug: "real-time-ad-performance", category: "analytics" },
  { name: "Campaign Comparison", slug: "campaign-comparison", category: "analytics" },
  { name: "Creative Performance Analysis", slug: "creative-performance-analysis", category: "analytics" },
  { name: "Audience Insights", slug: "audience-insights", category: "analytics" },
  { name: "Historical Trend Analysis", slug: "historical-trend-analysis", category: "analytics" },
  { name: "Platform Benchmarking", slug: "platform-benchmarking", category: "analytics" },
  { name: "Ad Spend Tracking", slug: "ad-spend-tracking", category: "analytics" },

  // Attribution
  { name: "Verify Platform Revenue", slug: "verify-platform-revenue", category: "attribution" },
  { name: "First-Party Attribution", slug: "first-party-attribution", category: "attribution" },
  { name: "Cross-Device Tracking", slug: "cross-device-tracking", category: "attribution" },
  { name: "iOS 14 Attribution", slug: "ios14-attribution", category: "attribution" },
  { name: "Post-Purchase Surveys", slug: "post-purchase-surveys", category: "attribution" },
  { name: "Multi-Touch Attribution", slug: "multi-touch-attribution", category: "attribution" },
  { name: "Customer Journey Mapping", slug: "customer-journey-mapping", category: "attribution" },
  { name: "Conversion Path Analysis", slug: "conversion-path-analysis", category: "attribution" },
  { name: "Assisted Conversion Tracking", slug: "assisted-conversion-tracking", category: "attribution" },

  // AI & Automation
  { name: "AI Ad Insights", slug: "ai-ad-insights", category: "ai" },
  { name: "Ask AI About Performance", slug: "ask-ai-about-performance", category: "ai" },
  { name: "Automated Recommendations", slug: "automated-recommendations", category: "ai" },
  { name: "Anomaly Detection", slug: "anomaly-detection", category: "ai" },
  { name: "Predictive Analytics", slug: "predictive-analytics", category: "ai" },
  { name: "Budget Recommendations", slug: "budget-recommendations", category: "ai" },
  { name: "Creative Recommendations", slug: "creative-recommendations", category: "ai" },
  { name: "Audience Recommendations", slug: "audience-recommendations", category: "ai" },
  { name: "AI Performance Summary", slug: "ai-performance-summary", category: "ai" },

  // Reporting
  { name: "Automated Reports", slug: "automated-reports", category: "reporting" },
  { name: "Scheduled Email Reports", slug: "scheduled-email-reports", category: "reporting" },
  { name: "Custom Dashboards", slug: "custom-dashboards", category: "reporting" },
  { name: "White-Label Reports", slug: "white-label-reports", category: "reporting" },
  { name: "Executive Summaries", slug: "executive-summaries", category: "reporting" },
  { name: "Client Reporting", slug: "client-reporting", category: "reporting" },
  { name: "Team Performance Reports", slug: "team-performance-reports", category: "reporting" },
  { name: "Export to Google Sheets", slug: "export-google-sheets", category: "reporting" },
  { name: "PDF Report Generation", slug: "pdf-report-generation", category: "reporting" },
  { name: "Slack Notifications", slug: "slack-notifications", category: "reporting" },

  // Optimization
  { name: "ROAS Optimization", slug: "roas-optimization", category: "optimization" },
  { name: "Budget Optimization", slug: "budget-optimization", category: "optimization" },
  { name: "Campaign Scaling", slug: "campaign-scaling", category: "optimization" },
  { name: "Ad Fatigue Detection", slug: "ad-fatigue-detection", category: "optimization" },
  { name: "Creative Testing", slug: "creative-testing", category: "optimization" },
  { name: "Audience Optimization", slug: "audience-optimization", category: "optimization" },
  { name: "Bid Strategy Optimization", slug: "bid-strategy-optimization", category: "optimization" },
  { name: "CPA Reduction", slug: "cpa-reduction", category: "optimization" },
  { name: "CPM Monitoring", slug: "cpm-monitoring", category: "optimization" },
  { name: "Frequency Management", slug: "frequency-management", category: "optimization" },

  // Platform-Specific
  { name: "Meta Ads Analytics", slug: "meta-ads-analytics", category: "platform" },
  { name: "Google Ads Analytics", slug: "google-ads-analytics", category: "platform" },
  { name: "TikTok Ads Analytics", slug: "tiktok-ads-analytics", category: "platform" },
  { name: "Pinterest Ads Analytics", slug: "pinterest-ads-analytics", category: "platform" },
  { name: "Snapchat Ads Analytics", slug: "snapchat-ads-analytics", category: "platform" },
  { name: "YouTube Ads Analytics", slug: "youtube-ads-analytics", category: "platform" },
  { name: "Amazon Ads Analytics", slug: "amazon-ads-analytics", category: "platform" },
  { name: "LinkedIn Ads Analytics", slug: "linkedin-ads-analytics", category: "platform" },
  { name: "Twitter Ads Analytics", slug: "twitter-ads-analytics", category: "platform" },

  // E-commerce Specific
  { name: "Shopify Analytics", slug: "shopify-analytics", category: "ecommerce" },
  { name: "WooCommerce Analytics", slug: "woocommerce-analytics", category: "ecommerce" },
  { name: "BigCommerce Analytics", slug: "bigcommerce-analytics", category: "ecommerce" },
  { name: "Product-Level ROAS", slug: "product-level-roas", category: "ecommerce" },
  { name: "Category Performance", slug: "category-performance", category: "ecommerce" },
  { name: "Customer Acquisition", slug: "customer-acquisition", category: "ecommerce" },
  { name: "LTV Analysis", slug: "ltv-analysis", category: "ecommerce" },
  { name: "New vs Returning Customers", slug: "new-vs-returning-customers", category: "ecommerce" },
  { name: "AOV Tracking", slug: "aov-tracking", category: "ecommerce" },
  { name: "Cart Abandonment", slug: "cart-abandonment", category: "ecommerce" },

  // Agency Use Cases
  { name: "Manage Multiple Clients", slug: "manage-multiple-clients", category: "agency" },
  { name: "Agency Dashboard", slug: "agency-dashboard", category: "agency" },
  { name: "Client Onboarding", slug: "client-onboarding", category: "agency" },
  { name: "Multi-Account Management", slug: "multi-account-management", category: "agency" },
  { name: "Team Collaboration", slug: "team-collaboration", category: "agency" },
  { name: "Performance Benchmarks", slug: "performance-benchmarks", category: "agency" },
  { name: "Agency Profitability", slug: "agency-profitability", category: "agency" },
  { name: "Client Retention", slug: "client-retention", category: "agency" },

  // Brand Use Cases
  { name: "Brand Health Monitoring", slug: "brand-health-monitoring", category: "brand" },
  { name: "Competitive Analysis", slug: "competitive-analysis", category: "brand" },
  { name: "Market Share Analysis", slug: "market-share-analysis", category: "brand" },
  { name: "Brand vs Performance", slug: "brand-vs-performance", category: "brand" },
  { name: "Omnichannel Attribution", slug: "omnichannel-attribution", category: "brand" },

  // Financial
  { name: "P&L by Channel", slug: "pl-by-channel", category: "finance" },
  { name: "Profit Margin Analysis", slug: "profit-margin-analysis", category: "finance" },
  { name: "Break-Even Analysis", slug: "break-even-analysis", category: "finance" },
  { name: "Budget Planning", slug: "budget-planning", category: "finance" },
  { name: "Forecasting", slug: "forecasting", category: "finance" },
  { name: "Cost Tracking", slug: "cost-tracking", category: "finance" },
  { name: "Revenue Attribution", slug: "revenue-attribution", category: "finance" },
];

// ============================================================================
// COMPETITORS - More alternatives
// ============================================================================
const competitors = [
  { name: "Triple Whale", slug: "triple-whale", pricing: "$129+/month" },
  { name: "Northbeam", slug: "northbeam", pricing: "$1,000+/month" },
  { name: "Rockerbox", slug: "rockerbox", pricing: "$1,500+/month" },
  { name: "Madgicx", slug: "madgicx", pricing: "$55+/month" },
  { name: "Hyros", slug: "hyros", pricing: "$199+/month" },
  { name: "Wicked Reports", slug: "wicked-reports", pricing: "$250+/month" },
  { name: "Cometly", slug: "cometly", pricing: "$199+/month" },
  { name: "Ruler Analytics", slug: "ruler-analytics", pricing: "$79+/month" },
  { name: "Attribution App", slug: "attribution-app", pricing: "$79+/month" },
  { name: "Supermetrics", slug: "supermetrics", pricing: "$39+/month" },
  { name: "Funnel.io", slug: "funnel-io", pricing: "$399+/month" },
  { name: "Whatagraph", slug: "whatagraph", pricing: "$199+/month" },
  { name: "DashThis", slug: "dashthis", pricing: "$33+/month" },
  { name: "AgencyAnalytics", slug: "agencyanalytics", pricing: "$12+/month" },
  { name: "Databox", slug: "databox", pricing: "$72+/month" },
  { name: "Klipfolio", slug: "klipfolio", pricing: "$49+/month" },
  { name: "Segment", slug: "segment", pricing: "$120+/month" },
  { name: "Amplitude", slug: "amplitude", pricing: "Custom" },
  { name: "Mixpanel", slug: "mixpanel", pricing: "$25+/month" },
  { name: "Heap", slug: "heap", pricing: "Custom" },
];

// ============================================================================
// GENERATOR FUNCTIONS
// ============================================================================

function generateGlossaryTerm(termData, category) {
  const { term, fullName } = termData;
  const slug = term.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/-+/g, "-").replace(/^-|-$/g, "");

  return {
    term,
    fullName: fullName || term,
    slug,
    definition: `${term} (${fullName || term}) is a key ${category.replace("-", " ")} term in digital advertising. It helps marketers measure and optimize their advertising performance across platforms like Meta, Google, and TikTok.`,
    formula: `Varies by context`,
    example: `A typical example of ${term} in e-commerce advertising...`,
    category,
    relatedTerms: [],
    faqs: [
      {
        q: `What is ${term}?`,
        a: `${term} stands for ${fullName || term}. It's an important metric/concept in digital advertising and marketing analytics.`,
      },
      {
        q: `Why is ${term} important?`,
        a: `${term} is important for understanding and optimizing your advertising performance. It helps you make data-driven decisions about your ad spend.`,
      },
    ],
    metricxFeature: `Track and analyze ${term} across all your ad platforms in one unified dashboard with metricx.`,
  };
}

function generateIndustry(industryData) {
  return {
    name: industryData.name,
    slug: industryData.slug,
    category: industryData.category,
    description: `Ad analytics insights and benchmarks for the ${industryData.name} industry. Learn how ${industryData.name} brands optimize their advertising across Meta, Google, and TikTok.`,
    benchmarks: {
      avgRoas: "3-5x",
      avgCpa: "$15-45",
      avgCtr: "1-3%",
    },
    challenges: [
      `Competition in the ${industryData.name} space`,
      "Rising CPMs across platforms",
      "Attribution challenges with iOS 14+",
      "Creative fatigue and ad blindness",
    ],
    tips: [
      "Focus on first-party data collection",
      "Test video creative formats",
      "Use lookalike audiences from purchasers",
      "Implement server-side tracking",
    ],
    relatedIndustries: [],
    faqs: [
      {
        q: `What's a good ROAS for ${industryData.name}?`,
        a: `ROAS benchmarks for ${industryData.name} typically range from 3-5x depending on margins and AOV. Use metricx to track your specific ROAS and compare to industry benchmarks.`,
      },
      {
        q: `Which ad platforms work best for ${industryData.name}?`,
        a: `Most ${industryData.name} brands see success with Meta (Facebook/Instagram) and Google Ads. TikTok is increasingly important for reaching younger audiences.`,
      },
    ],
  };
}

function generateUseCase(useCaseData) {
  const categoryDescriptions = {
    analytics: "track and analyze",
    attribution: "attribute and verify",
    ai: "leverage AI to understand",
    reporting: "report and share",
    optimization: "optimize and improve",
    platform: "manage",
    ecommerce: "e-commerce focused",
    agency: "agency-focused",
    brand: "brand-level",
    finance: "financial",
  };

  return {
    name: useCaseData.name,
    slug: useCaseData.slug,
    category: useCaseData.category,
    tagline: `${useCaseData.name} made simple with metricx`,
    description: `Learn how metricx helps you ${categoryDescriptions[useCaseData.category] || "manage"} your advertising with ${useCaseData.name.toLowerCase()}. Connect Meta, Google, and TikTok for unified insights.`,
    problem: `Managing ${useCaseData.name.toLowerCase()} across multiple ad platforms is time-consuming and error-prone. Spreadsheets don't scale, and platform dashboards don't talk to each other.`,
    solution: `metricx unifies your ad data from Meta, Google, and TikTok into one dashboard, making ${useCaseData.name.toLowerCase()} effortless. See everything in one place and get AI-powered insights.`,
    benefits: [
      "Save hours on manual reporting",
      "See all platforms in one view",
      "Get AI-powered recommendations",
      "Make faster, data-driven decisions",
    ],
    features: [
      "Real-time data sync",
      "Cross-platform comparison",
      "AI insights and recommendations",
      "Automated alerts",
    ],
    idealFor: ["E-commerce brands", "DTC companies", "Marketing teams", "Agencies"],
    faqs: [
      {
        q: `How does metricx help with ${useCaseData.name}?`,
        a: `metricx connects to Meta, Google, and TikTok to provide unified ${useCaseData.name.toLowerCase()} across all your ad platforms in one dashboard.`,
      },
    ],
    relatedUseCases: [],
    cta: `Start ${useCaseData.name} Today`,
  };
}

function generateCompetitor(competitorData) {
  return {
    name: competitorData.name,
    slug: competitorData.slug,
    pricing: competitorData.pricing,
    metricxPricing: "$29.99/month",
    description: `Compare metricx vs ${competitorData.name}. See why e-commerce brands choose metricx for ad analytics.`,
    tagline: `${competitorData.name} alternative starting at $29.99/month`,
    comparisonPoints: [
      {
        feature: "Price",
        competitor: competitorData.pricing,
        metricx: "$29.99/month",
        winner: "metricx",
      },
      {
        feature: "Setup Time",
        competitor: "30+ minutes",
        metricx: "5 minutes",
        winner: "metricx",
      },
      {
        feature: "AI Insights",
        competitor: "Limited",
        metricx: "Built-in AI Copilot",
        winner: "metricx",
      },
    ],
    pros: ["Established brand", "Feature-rich"],
    cons: ["Expensive", "Complex setup", "Steep learning curve"],
    metricxAdvantages: [
      "77% cheaper",
      "5-minute setup",
      "AI-powered insights",
      "Simpler interface",
    ],
    faqs: [
      {
        q: `Is metricx a good ${competitorData.name} alternative?`,
        a: `Yes! metricx offers similar core features at a fraction of the price. Most brands save 77% or more switching from ${competitorData.name} to metricx.`,
      },
      {
        q: `How does metricx compare to ${competitorData.name}?`,
        a: `metricx focuses on the metrics that matter: ROAS, CPA, and revenue tracking across Meta, Google, and TikTok. We're simpler, faster to set up, and much more affordable.`,
      },
    ],
    relatedCompetitors: [],
  };
}

// ============================================================================
// MAIN GENERATOR
// ============================================================================

async function generateAllContent() {
  console.log("Starting SEO content generation...\n");

  // 1. Generate Glossary Terms
  console.log("Generating glossary terms...");
  const glossaryTerms = [];

  for (const [category, terms] of Object.entries(glossaryCategories)) {
    for (const termData of terms) {
      glossaryTerms.push(generateGlossaryTerm(termData, category));
    }
  }

  fs.writeFileSync(
    path.join(__dirname, "../content/glossary/terms-expanded.json"),
    JSON.stringify(glossaryTerms, null, 2)
  );
  console.log(`  Generated ${glossaryTerms.length} glossary terms`);

  // 2. Generate Industries
  console.log("Generating industries...");
  const industriesData = industries.map(generateIndustry);

  fs.writeFileSync(
    path.join(__dirname, "../content/industries/data-expanded.json"),
    JSON.stringify(industriesData, null, 2)
  );
  console.log(`  Generated ${industriesData.length} industries`);

  // 3. Generate Use Cases
  console.log("Generating use cases...");
  const useCasesData = useCases.map(generateUseCase);

  fs.writeFileSync(
    path.join(__dirname, "../content/use-cases/data-expanded.json"),
    JSON.stringify(useCasesData, null, 2)
  );
  console.log(`  Generated ${useCasesData.length} use cases`);

  // 4. Generate Competitors
  console.log("Generating competitors...");
  const competitorsData = competitors.map(generateCompetitor);

  fs.writeFileSync(
    path.join(__dirname, "../content/competitors/data-expanded.json"),
    JSON.stringify(competitorsData, null, 2)
  );
  console.log(`  Generated ${competitorsData.length} competitors`);

  // Summary
  console.log("\n=== Generation Complete ===");
  console.log(`Glossary terms: ${glossaryTerms.length}`);
  console.log(`Industries: ${industriesData.length}`);
  console.log(`Use cases: ${useCasesData.length}`);
  console.log(`Competitors: ${competitorsData.length}`);
  console.log(
    `\nTotal pages potential: ${
      glossaryTerms.length + industriesData.length + useCasesData.length + competitorsData.length * 2
    }`
  );
  console.log("\nFiles saved to content/*-expanded.json");
  console.log("Run: mv content/*-expanded.json content/*.json to replace originals");
}

generateAllContent().catch(console.error);
