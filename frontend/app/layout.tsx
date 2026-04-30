import './globals.css';

export const metadata = {
  title: 'ElevatorAI - AI Elevator Cabin Designer',
  description: 'Upload your villa interior photo. Our AI agents analyze the style, match the perfect cabin design, generate a 3D preview, and send you a quote via WhatsApp.',
  keywords: 'elevator, cabin design, AI, interior design, 3D model, WhatsApp',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
