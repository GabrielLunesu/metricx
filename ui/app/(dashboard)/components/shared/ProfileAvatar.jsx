'use client'

/**
 * ProfileAvatar - User profile avatar with gradient border
 * Features:
 * - Gradient border
 * - Shadow on hover
 * - Displays user initial or avatar image
 */
export default function ProfileAvatar({
    initial = "U",
    imageUrl = null,
    onClick = null
}) {
    const avatarContent = imageUrl ? (
        <img
            src={imageUrl}
            className="w-full h-full rounded-full border-2 border-white object-cover"
            alt="Profile"
        />
    ) : (
        <div className="w-full h-full rounded-full border-2 border-white bg-gradient-to-br from-slate-200 to-slate-300 flex items-center justify-center text-slate-600 text-xs font-bold">
            {initial}
        </div>
    );

    if (onClick) {
        return (
            <button
                onClick={onClick}
                className="w-9 h-9 rounded-full p-[2px] bg-gradient-to-tr from-cyan-300 to-blue-400 cursor-pointer hover:shadow-lg hover:shadow-cyan-200/50 transition-shadow"
            >
                {avatarContent}
            </button>
        );
    }

    return (
        <div className="w-9 h-9 rounded-full p-[2px] bg-gradient-to-tr from-cyan-300 to-blue-400 cursor-pointer hover:shadow-lg hover:shadow-cyan-200/50 transition-shadow">
            {avatarContent}
        </div>
    );
}
