import Script from "next/script";

import {
  SHOPIFY_API_KEY,
  SHOPIFY_APP_BRIDGE_CDN_URL,
} from "@/lib/shopifyConfig";

export const metadata = {
  other: {
    "shopify-api-key": SHOPIFY_API_KEY,
  },
};

export default function ShopifyLayout({ children }) {
  return (
    <>
      <Script src={SHOPIFY_APP_BRIDGE_CDN_URL} strategy="beforeInteractive" />
      {children}
    </>
  );
}
