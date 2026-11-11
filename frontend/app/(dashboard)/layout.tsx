import { AppSidebar } from "@/common/sidebar";
import { Header } from "@/common/header";
import { SidebarProvider } from "@/components/ui/sidebar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <SidebarProvider>
      <AppSidebar />
      <div className="relative flex min-w-0 flex-1 flex-col bg-background">
        <Header />
        <main className="flex flex-1 flex-col">{children}</main>
      </div>
    </SidebarProvider>
  );
}
