import type { Metadata } from 'next'
import { Plus_Jakarta_Sans } from 'next/font/google'
import './globals.css'

const jakarta = Plus_Jakarta_Sans({
  subsets: ['latin'],
  variable: '--font-display',
  weight: ['500', '600', '700', '800'],
})

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
        <script dangerouslySetInnerHTML={{
          __html: `(function(){try{var t=localStorage.getItem('theme');if(t==='light'){document.documentElement.classList.remove('dark')}else if(t==='dark'){document.documentElement.classList.add('dark')}else{if(window.matchMedia('(prefers-color-scheme: light)').matches){document.documentElement.classList.remove('dark')}else{document.documentElement.classList.add('dark')}}}catch(e){}})()`
        }} />
      </head>
      <body className={`${jakarta.variable} font-sans`}>{children}</body>
    </html>
  )
}
