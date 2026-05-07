import { Dashboard } from "@/components/Dashboard";
import { loadSnapshots } from "@/lib/data";

export default async function Home() {
  const snapshots = await loadSnapshots();
  return <Dashboard snapshots={snapshots} />;
}
