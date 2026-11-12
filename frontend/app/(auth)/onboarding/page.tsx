import type { Metadata } from "next";

import { OnboardingView } from "@/views/onboarding";

export const metadata: Metadata = {
  title: "Device onboarding",
};

export default function OnboardingPage() {
  return <OnboardingView />;
}
