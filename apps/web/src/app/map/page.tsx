import { Shell } from "@/components/Shell";
import { MapView } from "@/features/map/MapView";

export default function MapPage() {
  return (
    <Shell
      title="Map"
      lede="Your facts, your openings and the beliefs derived from them, drawn with the links between them."
    >
      <MapView />
    </Shell>
  );
}
