import './globals.css';
import { AuthProvider } from '../components/auth-provider';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Toruqx | Secure Enterprise RAG Engine',
  description: 'Toruqx: Production-grade Conversational AI search and citation grounding platform',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark scroll-smooth">
      <body className="min-h-screen flex flex-col font-sans overflow-x-hidden bg-background text-foreground selection:bg-primary/10">
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
