import { Shell } from "@/components/Shell";
import { QuestionsView } from "@/features/questions/QuestionsView";

export default function QuestionsPage() {
  return (
    <Shell
      title="Questions"
      lede="When a change leaves a belief Ripple cannot re-check on its own, it parks it here and asks you."
    >
      <QuestionsView />
    </Shell>
  );
}
