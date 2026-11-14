import type { Metadata } from "next";

import { OnboardingView } from "@/views/onboarding";

export const metadata: Metadata = {
  title: "Add device",
};

// The onboarding wizard now lives inside the station dashboard, so the admin
// can register another controller without leaving the console.
export default function AddDevicePage() {
  return (
    <div className="flex flex-1 justify-center p-4 lg:p-6">
      <OnboardingView />
    </div>
  );
}
