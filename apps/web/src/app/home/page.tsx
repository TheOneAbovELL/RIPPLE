import { Shell } from "@/components/Shell";
import { HomeView } from "@/features/home/HomeView";

export default function Page() {
  return (
    <Shell title="Home" lede="What needs you, what changed, and what Ripple knows about you.">
      <HomeView />
    </Shell>
  );
}
