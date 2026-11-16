import type { Metadata } from "next";

import { StationsView } from "@/views/stations";

export const metadata: Metadata = {
  title: "Stations",
};

export default function StationsPage() {
  return <StationsView />;
}
