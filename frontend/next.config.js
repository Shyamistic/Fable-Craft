/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  env: {
    // Empty string means the frontend calls its own origin (/api/...)
    // Next.js rewrites then proxy to the actual backend
    NEXT_PUBLIC_API_URL: '',
  },
  async rewrites() {
    // BACKEND_URL is a server-side-only env var (set in Amplify)
    // It proxies /api/* requests to the actual backend server
    const backendUrl = process.env.BACKEND_URL || 'http://54.88.159.186:8080'
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
