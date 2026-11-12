import { Suspense } from "react";
import type { Metadata } from "next";

import { AccessLogsView } from "@/views/access-logs";

export const metadata: Metadata = {
  title: "Access Logs",
};

export default function LogsPage() {
  return (
    <Suspense fallback={null}>
      <AccessLogsView />
    </Suspense>
  );
}
