import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'SIDAGI - Sistem Dokumentasi Arsip Digital BWS Maluku Utara',
  description: 'Sistem Dokumentasi Arsip Digital BWS Maluku Utara',
  icons: {
    icon: '/logo.png',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="id" suppressHydrationWarning>
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap"
          rel="stylesheet"
        />
        <script dangerouslySetInnerHTML={{
          __html: `(function(){try{var t=localStorage.getItem('theme');if(t==='light'){document.documentElement.classList.remove('dark')}else if(t==='dark'){document.documentElement.classList.add('dark')}else{if(window.matchMedia('(prefers-color-scheme: light)').matches){document.documentElement.classList.remove('dark')}else{document.documentElement.classList.add('dark')}}}catch(e){}})()`
        }} />
      </head>
      <body style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>{children}</body>
    </html>
  )
}
