// 사이드바와 Ask 화면은 대화 목록을 각자 들고 있다. 새 대화는 history.replaceState로 주소만
// 바꾸므로 usePathname이 달라지지 않는다. 이 알림이 없으면 새로고침 전까지 사이드바 목록과
// 크레딧 잔액이 그대로 남는다.
const ASK_THREADS_CHANGED_EVENT = "nexuswiki:ask-threads-changed";

export type AskThreadsChangeSource = "sidebar" | "conversation";

export function notifyAskThreadsChanged(source: AskThreadsChangeSource): void {
  window.dispatchEvent(
    new CustomEvent<AskThreadsChangeSource>(ASK_THREADS_CHANGED_EVENT, {
      detail: source,
    }),
  );
}

// 보낸 쪽은 자기 목록을 이미 고쳤으므로 자기 알림을 받지 않는다.
export function subscribeAskThreadsChanged(
  self: AskThreadsChangeSource,
  listener: () => void,
): () => void {
  function handle(event: Event) {
    if ((event as CustomEvent<AskThreadsChangeSource>).detail !== self) {
      listener();
    }
  }
  window.addEventListener(ASK_THREADS_CHANGED_EVENT, handle);
  return () => window.removeEventListener(ASK_THREADS_CHANGED_EVENT, handle);
}
