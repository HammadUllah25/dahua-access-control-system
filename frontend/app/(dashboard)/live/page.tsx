import type { Metadata } from "next";

import { LiveMonitoringView } from "@/views/live-monitoring";

export const metadata: Metadata = {
  title: "Live Monitoring",
};

export default function LivePage() {
  return <LiveMonitoringView />;
}
