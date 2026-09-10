import { YoutubeChannelSearch } from "@/components/YoutubeChannelSearch";

type YoutubePageProps = {
  params: Promise<{ workspaceId: string }>;
};

// YouTube 수집 진입 라우트 (youtube-channel-import 슬라이스 1).
//
// 이 파일은 Server Component로 남지만 초기 데이터를 읽지 않는다 — 채널 검색은
// 워크스페이스 DB가 아니라 워커 뒤의 외부 API를 소비하므로 서버 렌더 시점에
// 미리 부를 것이 없고, 부르면 페이지 진입만으로 공용 쿼터가 타들어간다.
// 검색은 사용자가 실제로 키워드를 넣었을 때만 일어난다.
export default async function YoutubePage({ params }: YoutubePageProps) {
  const { workspaceId } = await params;

  return (
    <div className="content">
      <section className="hero" data-od-id="youtube-import-header">
        <div>
          <h1>YouTube 수집</h1>
          <p>
            채널을 검색해 원하는 영상을 고르면, 자막을 원문 소스로 수집합니다.
          </p>
        </div>
      </section>

      <YoutubeChannelSearch workspaceId={workspaceId} />
    </div>
  );
}
