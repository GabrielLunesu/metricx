/**
 * Modern Glassmorphic Loading Animation
 * 
 * WHAT: Premium SVG-based loader with glassmorphism effects
 * WHY: Enhances perceived performance and matches the app's premium aesthetic
 */

export default function LoadingAnimation({ message = "Loading..." }) {
  return (
    <div className="min-h-[400px] flex flex-col items-center justify-center p-8">
      <div className="relative w-32 h-32">
        {/* Glassmorphic SVG Loader */}
        <svg className="w-full h-full animate-spin-slow" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="glass-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="rgba(255, 255, 255, 0.8)" />
              <stop offset="50%" stopColor="rgba(255, 255, 255, 0.1)" />
              <stop offset="100%" stopColor="rgba(255, 255, 255, 0.4)" />
            </linearGradient>
            <linearGradient id="cyan-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#22d3ee" />
              <stop offset="100%" stopColor="#0ea5e9" />
            </linearGradient>
            <filter id="glass-blur" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur in="SourceGraphic" stdDeviation="2" />
            </filter>
          </defs>

          {/* Background Ring (Frosted) */}
          <circle cx="50" cy="50" r="40" stroke="url(#glass-gradient)" strokeWidth="6" strokeLinecap="round" className="opacity-40" />

          {/* Rotating Arc (Cyan) */}
          <path d="M 50 10 a 40 40 0 0 1 40 40" stroke="url(#cyan-gradient)" strokeWidth="6" strokeLinecap="round">
            {/* SVG internal animation for smoothness independent of CSS */}
            <animateTransform attributeName="transform" type="rotate" from="0 50 50" to="360 50 50" dur="1.5s" repeatCount="indefinite" />
          </path>

          {/* Inner Glass Circle */}
          <circle cx="50" cy="50" r="25" fill="url(#glass-gradient)" className="opacity-30" filter="url(#glass-blur)" />
        </svg>

        {/* Center Glow */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="w-20 h-20 bg-cyan-400/20 rounded-full blur-2xl animate-pulse"></div>
        </div>
      </div>

      {/* Message */}
      <div className="mt-8 flex flex-col items-center gap-3">
        <p className="text-slate-500 font-medium animate-pulse tracking-wide text-sm uppercase">{message}</p>
        <div className="flex gap-1.5">
          <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce" style={{ animationDelay: '0ms' }}></div>
          <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce" style={{ animationDelay: '150ms' }}></div>
          <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce" style={{ animationDelay: '300ms' }}></div>
        </div>
      </div>
    </div>
  );
}
