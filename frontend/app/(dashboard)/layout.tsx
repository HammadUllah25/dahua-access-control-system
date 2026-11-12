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
        <main className="relative isolate flex flex-1 flex-col">
          {/* ambient accent glow behind the page content */}
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 -z-10 overflow-hidden"
          >
            <div className="absolute -top-40 right-[-10%] size-[36rem] rounded-full bg-primary/10 blur-3xl" />
            <div className="absolute bottom-[-12rem] left-[-8rem] size-[30rem] rounded-full bg-primary/[0.06] blur-3xl" />
          </div>
          {children}
        </main>
      </div>
    </SidebarProvider>
  );
}
