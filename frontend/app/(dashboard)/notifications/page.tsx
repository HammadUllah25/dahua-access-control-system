import type { Metadata } from "next";

import { NotificationsView } from "@/views/notifications";

export const metadata: Metadata = {
  title: "Notifications",
};

export default function NotificationsPage() {
  return <NotificationsView />;
}
