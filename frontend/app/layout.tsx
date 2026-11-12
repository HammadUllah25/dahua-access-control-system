import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ToastProvider } from "@/components/toast-provider";
import "./globals.css";

const plexSans = IBM_Plex_Sans({
  variable: "--font-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Washroom Access · Station Admin",
    template: "%s · Washroom Access",
  },
  description:
    "Station admin console for washroom card access, people, schedules and door events.",
  icons: { icon: "/fevicon.ico" },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${plexSans.variable} ${plexMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <TooltipProvider>
          {children}
          <ToastProvider />
        </TooltipProvider>
      </body>
    </html>
  );
}
