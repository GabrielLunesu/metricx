import { ClerkProvider } from '@clerk/nextjs';
import { Analytics } from '@vercel/analytics/react';
import { Toaster } from 'sonner';
import '@/app/globals.css';

const signInFallbackRedirectUrl =
  process.env.NEXT_PUBLIC_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL ||
  process.env.NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL ||
  '/dashboard';

const signUpFallbackRedirectUrl =
  process.env.NEXT_PUBLIC_CLERK_SIGN_UP_FALLBACK_REDIRECT_URL ||
  process.env.NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL ||
  '/onboarding';

export default function App({ Component, pageProps }) {
  return (
    <ClerkProvider
      signInFallbackRedirectUrl={signInFallbackRedirectUrl}
      signUpFallbackRedirectUrl={signUpFallbackRedirectUrl}
    >
      <Component {...pageProps} />
      <Analytics />
      <Toaster
        position="top-right"
        richColors
        closeButton
        expand
        toastOptions={{
          duration: 4000,
          style: {
            borderRadius: '16px',
            border: '1px solid rgba(0,0,0,0.06)',
          },
        }}
      />
    </ClerkProvider>
  );
}
