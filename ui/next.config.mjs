/** @type {import('next').NextConfig} */
const nextConfig = {
    reactCompiler: true,
    async redirects() {
        return [
            {
                source: '/signup',
                destination: '/sign-up',
                permanent: true,
            },
        ]
    },
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
