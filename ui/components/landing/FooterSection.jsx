"use client";

/**
 * FooterSection - Minimal, clean footer with essential links
 * Related: page.jsx
 */

export default function FooterSection() {
  return (
    <footer className="w-full bg-white border-t border-gray-100">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-6">
          {/* Brand */}
          <div className="flex items-center gap-6">
            <a href="/" className="flex items-center">
              <img src="/logo.png" alt="metricx" className="h-7" />
            </a>
            <div className="hidden sm:flex items-center gap-4 text-sm">
              <a href="#features" className="text-gray-500 hover:text-gray-900 transition-colors">
                Features
              </a>
              <a href="#pricing" className="text-gray-500 hover:text-gray-900 transition-colors">
                Pricing
              </a>
              <a href="/privacy" className="text-gray-500 hover:text-gray-900 transition-colors">
                Privacy
              </a>
              <a href="/terms" className="text-gray-500 hover:text-gray-900 transition-colors">
                Terms
              </a>
            </div>
          </div>

          {/* Right side */}
          <div className="flex items-center gap-4">
            {/* Social */}
            <a
              href="https://twitter.com"
              target="_blank"
              rel="noopener noreferrer"
              className="w-8 h-8 flex items-center justify-center rounded-full bg-gray-100 text-gray-500 hover:bg-gray-200 hover:text-gray-700 transition-all"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
              </svg>
            </a>
            <a
              href="https://linkedin.com"
              target="_blank"
              rel="noopener noreferrer"
              className="w-8 h-8 flex items-center justify-center rounded-full bg-gray-100 text-gray-500 hover:bg-gray-200 hover:text-gray-700 transition-all"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M20.5 2h-17A1.5 1.5 0 002 3.5v17A1.5 1.5 0 003.5 22h17a1.5 1.5 0 001.5-1.5v-17A1.5 1.5 0 0020.5 2zM8 19H5v-9h3zM6.5 8.25A1.75 1.75 0 118.3 6.5a1.78 1.78 0 01-1.8 1.75zM19 19h-3v-4.74c0-1.42-.6-1.93-1.38-1.93A1.74 1.74 0 0013 14.19a.66.66 0 000 .14V19h-3v-9h2.9v1.3a3.11 3.11 0 012.7-1.4c1.55 0 3.36.86 3.36 3.66z" />
              </svg>
            </a>
            <span className="text-gray-300">|</span>
            <p className="text-gray-400 text-sm">
              © 2025 metricx
            </p>
          </div>
        </div>

        {/* Mobile links */}
        <div className="flex sm:hidden items-center justify-center gap-4 mt-4 text-sm">
          <a href="#features" className="text-gray-500 hover:text-gray-900 transition-colors">
            Features
          </a>
          <a href="#pricing" className="text-gray-500 hover:text-gray-900 transition-colors">
            Pricing
          </a>
          <a href="/privacy" className="text-gray-500 hover:text-gray-900 transition-colors">
            Privacy
          </a>
          <a href="/terms" className="text-gray-500 hover:text-gray-900 transition-colors">
            Terms
          </a>
        </div>
      </div>
    </footer>
  );
}
