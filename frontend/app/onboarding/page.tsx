import { redirect } from "next/navigation";

// Onboarding moved into the dashboard as the Add Device flow. Keep this entry
// point so existing signup/OTP links keep working.
export default function OnboardingPage() {
  redirect("/add-device");
}
