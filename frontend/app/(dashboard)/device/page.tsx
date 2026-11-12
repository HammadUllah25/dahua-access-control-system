import type { Metadata } from "next";

import { DeviceDoorView } from "@/views/device-door";

export const metadata: Metadata = {
  title: "Device & Door",
};

export default function DevicePage() {
  return <DeviceDoorView />;
}
