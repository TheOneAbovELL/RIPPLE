import { Shell } from "@/components/Shell";
import { OpeningsView } from "@/features/openings/OpeningsView";

export default function Page() {
  return (
    <Shell
      title="Add an opening"
      lede="Paste a job description and Ripple records it, shows where each detail came from, and checks it against your profile."
    >
      <OpeningsView />
    </Shell>
  );
}
