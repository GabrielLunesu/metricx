import Document, { Head, Html, Main, NextScript } from 'next/document';
import { SHOPIFY_API_KEY, SHOPIFY_APP_BRIDGE_CDN_URL } from '@/lib/shopifyConfig';

export default class MyDocument extends Document {
  static async getInitialProps(ctx) {
    const initialProps = await Document.getInitialProps(ctx);
    return {
      ...initialProps,
      pathname: ctx.pathname,
    };
  }

  render() {
    const isShopifyPage = this.props.pathname === '/shopify';

    return (
      <Html lang="en">
        <Head>
          {isShopifyPage ? (
            <>
              <meta name="shopify-api-key" content={SHOPIFY_API_KEY} />
              <script src={SHOPIFY_APP_BRIDGE_CDN_URL} />
            </>
          ) : null}
          <link rel="preconnect" href="https://fonts.googleapis.com" />
          <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
          <link
            href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap"
            rel="stylesheet"
          />
        </Head>
        <body className="antialiased overflow-x-hidden">
          <Main />
          <NextScript />
        </body>
      </Html>
    );
  }
}
