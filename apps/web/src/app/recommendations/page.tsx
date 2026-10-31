import { Shell } from "@/components/Shell";
import { RecommendationsView } from "@/features/recommendations/RecommendationsView";

export default function RecommendationsPage() {
  return (
    <Shell
      title="Recommendations"
      lede="Openings ranked by fit, with eligibility and the reasons behind each verdict."
    >
      <RecommendationsView />
    </Shell>
  );
}
