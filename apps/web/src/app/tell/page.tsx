import { Shell } from "@/components/Shell";
import { TellView } from "@/features/tell/TellView";

export default function Page() {
  return (
    <Shell
      title="Say what changed"
      lede="A new CGPA, an offer you accepted, a skill you picked up: tell Ripple, and it re-checks everything that depended on it."
    >
      <TellView />
    </Shell>
  );
}
