import type { Metadata } from "next";
import { EvaluationView } from "./EvaluationView";

export const metadata: Metadata = { title: "Evaluation" };

export default function EvaluationPage() {
  return <EvaluationView />;
}
