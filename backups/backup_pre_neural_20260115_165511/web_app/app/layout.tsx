import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { BettingSlipProvider } from "../contexts/BettingSlipContext";
import AutoValidator from "../components/AutoValidator";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Cortex Bet Pro | PhD Sports Analytics",
  description: "Advanced Bayesian Sports Prediction Engine",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <BettingSlipProvider>
          <AutoValidator />
          {children}
        </BettingSlipProvider>
      </body>
    </html>
  );
}
