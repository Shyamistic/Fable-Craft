import type { Metadata, Viewport } from 'next'
import { BRAND_NAME, BRAND_TAGLINE, BRAND_FONT_URL, BRAND_TYPEFACE, BRAND_COLORS } from '@/lib/branding'
import './globals.css'

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  minimumScale: 1,
  maximumScale: 5,
  userScalable: true,
}

export const metadata: Metadata = {
  title: BRAND_NAME,
  description: BRAND_TAGLINE,
  openGraph: {
    title: BRAND_NAME,
    description: BRAND_TAGLINE,
    siteName: BRAND_NAME,
    type: 'website',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <head>
        <link href={BRAND_FONT_URL} rel="stylesheet" />
        <meta name="theme-color" content={BRAND_COLORS.primary} />
        <link rel="icon" href="/logo-placeholder.svg" />
      </head>
      <body
        style={{
          fontFamily: `'${BRAND_TYPEFACE}', sans-serif`,
          color: '#1a1a1a',
          margin: 0,
          padding: 0,
          minHeight: '100vh',
          overflowX: 'hidden',
          maxWidth: '100vw',
        }}
      >
        {children}
      </body>
    </html>
  )
}
