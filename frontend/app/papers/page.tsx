import { Suspense } from "react";
import PaperWorkbench from "@/components/PaperWorkbench";

export default function PapersPage() {
  return (
    <Suspense fallback={<div className="card text-slate-600">Loading paper workspace...</div>}>
      <PaperWorkbench />
    </Suspense>
  );
}
