import { Suspense } from "react";
import type { Metadata } from "next";

import { OtpVerificationForm } from "@/components/auth/forms/otp-verification-form";

export const metadata: Metadata = {
  title: "Verify code",
};

export default function VerifyPage() {
  return (
    <Suspense fallback={null}>
      <OtpVerificationForm />
    </Suspense>
  );
}
