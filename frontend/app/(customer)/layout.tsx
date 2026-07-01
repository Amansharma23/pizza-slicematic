import { AppHeader } from "@/components/customer/app-header";
import { GlobalCart } from "@/components/customer/global-cart";
import { TabBar } from "@/components/customer/tab-bar";

/**
 * Customer surface shell — its OWN layout (header + bottom tab bar), independent
 * of the (staff) and (admin) groups. Shares only the root layout (fonts/theme).
 */
export default function CustomerLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Phone-first: on desktop the customer app sits in a centered phone-width
  // frame (backdrop gutters + borders); on a real phone it fills the screen.
  return (
    <div className="flex min-h-dvh justify-center bg-backdrop">
      <div className="relative flex h-dvh w-full max-w-md flex-col overflow-hidden bg-background shadow-2xl sm:border-x sm:border-border">
        <AppHeader />
        <main className="min-h-0 flex-1">{children}</main>
        <TabBar />
        <GlobalCart />
      </div>
    </div>
  );
}
