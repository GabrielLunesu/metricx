'use client'

/**
 * LogoMark - Animated logo component
 * Features:
 * - Gradient background
 * - Shimmer effect on hover
 * - Displays workspace initial or fallback
 */
export default function LogoMark({ initial = "AN", href = "/dashboard" }) {
    return (
        <a
            href={href}
            className="w-10 h-10 flex items-center justify-center rounded-xl bg-gradient-to-br from-slate-800 to-slate-900 text-white shadow-xl shadow-slate-300/50 mb-8 cursor-pointer group relative overflow-hidden"
        >
            {/* Shimmer effect */}
            <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-white/20 to-transparent rotate-45 translate-y-full group-hover:-translate-y-full transition-transform duration-700"></div>

            <span className="font-bold text-xs tracking-tighter relative z-10">
                {initial}
            </span>
        </a>
    );
}
