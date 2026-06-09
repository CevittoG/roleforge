/** @type {import('next').NextConfig} */
const isDev = process.env.NODE_ENV !== 'production';

const nextConfig = {
  output: 'export',
  trailingSlash: true,
  reactStrictMode: true,
  images: { unoptimized: true },
  ...(isDev
    ? {
        async rewrites() {
          return [
            {
              source: '/api/:path*',
              destination: 'http://127.0.0.1:8000/api/:path*',
            },
          ];
        },
      }
    : {}),
};

module.exports = nextConfig;
