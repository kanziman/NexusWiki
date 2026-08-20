import { PreviewWorkspace } from "@/components/PreviewWorkspace";

type PreviewPageProps = {
  params: Promise<{ path?: string[] }>;
};

export default async function PreviewPage({ params }: PreviewPageProps) {
  const { path = [] } = await params;
  return <PreviewWorkspace path={path} />;
}
