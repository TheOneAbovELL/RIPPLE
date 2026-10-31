import { Shell } from "@/components/Shell";
import { ResumeView } from "@/features/resume/ResumeView";

export default function Page() {
  return (
    <Shell
      title="Resume"
      lede="Upload your resume, then confirm the facts Ripple found. Nothing is saved until you do."
    >
      <ResumeView />
    </Shell>
  );
}
