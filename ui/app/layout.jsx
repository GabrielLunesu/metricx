// Global app layout. Provides HTML shell and imports global CSS.
// No dashboard chrome here; that lives in the dashboard layout.
import "./globals.css";
import AppProviders from "./providers";

export const metadata = {
  title: "metricx",
  description: "metricx - AI Marketing Assistant",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="bg-white antialiased overflow-x-hidden">
        {/* Cyan Aura Background Effects */}
        <div className="fixed inset-0 pointer-events-none overflow-hidden -z-10">
          <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-cyan-400 rounded-full blur-[120px] opacity-15 aura-glow"></div>
          <div className="absolute top-1/3 left-1/4 w-[400px] h-[400px] bg-cyan-300 rounded-full blur-[100px] opacity-10 float-orb" style={{ animationDelay: '1s' }}></div>
          <div className="absolute bottom-1/4 right-1/3 w-[350px] h-[350px] bg-cyan-500 rounded-full blur-[90px] opacity-10 float-orb" style={{ animationDelay: '2.5s' }}></div>
        </div>

        <AppProviders>
          {children}
        </AppProviders>
      </body>
    </html>
  );
}
