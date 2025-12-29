/** @type {import('next').NextConfig} */
const nextConfig = {
    reactCompiler: true,
    async rewrites() {
        return [
            {
                source: '/api/:path*',
                destination: `${process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'}/:path*`,
            },
        ]
    },
};

export default nextConfig;
