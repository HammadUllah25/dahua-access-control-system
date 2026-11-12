import type { Metadata } from "next";

import { AlertsEventsView } from "@/views/alerts-events";

export const metadata: Metadata = {
  title: "Alerts & Events",
};

export default function AlertsPage() {
  return <AlertsEventsView />;
}
