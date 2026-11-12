import type { Metadata } from "next";

import { AccessSchedulesView } from "@/views/access-schedules";

export const metadata: Metadata = {
  title: "Access Schedules",
};

export default function SchedulesPage() {
  return <AccessSchedulesView />;
}
