import { HealthBadge } from "@/components/HealthBadge";

export default function Home() {
  return (
    <main>
      <h1>NexusWiki</h1>
      <HealthBadge status="unknown" />
    </main>
  );
}
