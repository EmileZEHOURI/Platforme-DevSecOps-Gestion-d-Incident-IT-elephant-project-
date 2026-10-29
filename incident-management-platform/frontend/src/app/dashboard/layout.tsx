import { AuthProvider } from "@/components/auth-provider";
import { AppShell } from "@/components/app-shell";
export default function DashboardLayout({ children }: { children: React.ReactNode }) { return <AuthProvider><AppShell>{children}</AppShell></AuthProvider>; }
