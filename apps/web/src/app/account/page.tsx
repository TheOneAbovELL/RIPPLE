import { Shell } from "@/components/Shell";
import { AccountView } from "@/features/account/AccountView";

export default function AccountPage() {
  return (
    <Shell
      title="Account"
      lede="Link Telegram, download everything Ripple holds about you, or delete it."
    >
      <AccountView />
    </Shell>
  );
}
