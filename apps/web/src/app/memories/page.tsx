import { Shell } from "@/components/Shell";
import { MemoriesView } from "@/features/memories/MemoriesView";

export default function MemoriesPage() {
  return (
    <Shell
      title="Beliefs"
      lede="Everything Ripple currently believes about you, with its state and why it is held."
    >
      <MemoriesView />
    </Shell>
  );
}
