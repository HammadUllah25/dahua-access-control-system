import type { Metadata } from "next";

import { DeviceDoorView } from "@/views/device-door";

export const metadata: Metadata = {
  title: "Door & Sensor",
};

export default function DevicePage() {
  return <DeviceDoorView />;
}
