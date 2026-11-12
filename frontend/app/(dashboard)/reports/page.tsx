import type { Metadata } from "next";

import { ReportsView } from "@/views/reports";

export const metadata: Metadata = {
  title: "Reports",
};

export default function ReportsPage() {
  return <ReportsView />;
}
