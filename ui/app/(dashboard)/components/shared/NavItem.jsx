'use client'

/**
 * NavItem - Reusable navigation item with glassmorphism effects
 * Features:
 * - Glassmorphic hover effects
 * - Smooth transitions and scale animations
 * - Tooltip on hover
 * - Active state styling
 */
export default function NavItem({ href, label, icon: Icon, isActive }) {
    return (
        <div className="group relative flex justify-center w-full">
            {/* Glow effect on hover */}
            <div className="absolute inset-0 bg-gradient-to-r from-cyan-400/20 to-blue-400/20 blur-md opacity-0 group-hover:opacity-100 transition-opacity rounded-full"></div>

            <a
                href={href}
                className={`relative p-3 rounded-xl transition-all duration-300 group-hover:scale-110 ${isActive
                        ? 'text-cyan-600 bg-cyan-50/50 ring-1 ring-cyan-100 shadow-inner'
                        : 'text-slate-400 hover:text-cyan-600 hover:bg-white/60'
                    }`}
            >
                <Icon className="w-5 h-5" />
            </a>

            {/* Tooltip */}
            <div className="absolute left-16 top-2 px-3 py-1 glass-panel rounded-lg text-[10px] font-medium text-slate-600 opacity-0 group-hover:opacity-100 transition-all duration-300 translate-x-2 group-hover:translate-x-0 pointer-events-none whitespace-nowrap z-50">
                {label}
            </div>
        </div>
    );
}
