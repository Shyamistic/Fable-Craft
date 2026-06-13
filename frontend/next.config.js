/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  env: {
    // Set at build time. On EC2: same IP, port 8080.
    // On Amplify/HTTPS: leave empty and use rewrites.
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || '',
  },
}

module.exports = nextConfig
