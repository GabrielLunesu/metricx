import Head from 'next/head';
import ShopifyEmbeddedPage from '@/components/shopify/ShopifyEmbeddedPage';

export default function ShopifyPage() {
  return (
    <>
      <Head>
        <title>metricx - Shopify</title>
      </Head>
      <ShopifyEmbeddedPage />
    </>
  );
}
