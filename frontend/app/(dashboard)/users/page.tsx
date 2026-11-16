import type { Metadata } from "next";

import { UsersView } from "@/views/users";

export const metadata: Metadata = {
  title: "Users & Roles",
};

export default function UsersPage() {
  return <UsersView />;
}
