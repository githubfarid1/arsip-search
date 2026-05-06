import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Arsip Finder - BWS Maluku Utara',
  description: 'Sistem Pencarian Arsip BWS Maluku Utara',
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
        <script dangerouslySetInnerHTML={{
          __html: `(function(){try{var t=localStorage.getItem('theme');if(t==='light'){document.documentElement.classList.remove('dark')}else if(t==='dark'){document.documentElement.classList.add('dark')}else{if(window.matchMedia('(prefers-color-scheme: light)').matches){document.documentElement.classList.remove('dark')}else{document.documentElement.classList.add('dark')}}}catch(e){}})()`
        }} />
      </head>
      <body>{children}</body>
    </html>
  )
}
