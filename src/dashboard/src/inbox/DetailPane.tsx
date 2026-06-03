// Centre column — customer head + tab bar + the active tab's body.
// Pure presentation; all state is owned by InboxPage.
import type { InboxCustomerDetail } from "../api";
import { CustomerHead } from "./CustomerHead";
import { EmailDraftView } from "./EmailDraftView";
import { HistoryView } from "./HistoryView";
import { ReasoningView } from "./ReasoningView";
import { TabBar } from "./TabBar";
import type { InboxTab } from "./TabBar";
import { Sk } from "./ui";

export function DetailPane({
  detail,
  error,
  tab,
  onTab,
  isSent,
  onSend,
  threshold,
  modelVersion,
}: {
  detail?: InboxCustomerDetail;
  error?: string;
  tab: InboxTab;
  onTab: (t: InboxTab) => void;
  isSent: boolean;
  onSend: () => void;
  threshold: number;
  modelVersion: string;
}) {
  return (
    <section className="flex min-w-0 flex-1 flex-col bg-[var(--surface-soft)]">
      {error && !detail ? (
        <div className="m-6 rounded-lg border border-[var(--line)] bg-[var(--surface)] p-6 text-[12.5px] text-[var(--risk)]">
          {error} — couldn't load this customer. Pick another from the queue.
        </div>
      ) : !detail ? (
        <>
          <div className="bg-[var(--surface)] px-6 pt-5">
            <Sk className="mb-4 h-11 w-72" />
          </div>
          <div className="border-b border-[var(--line)] bg-[var(--surface)] px-6 pb-2.5">
            <Sk className="h-4 w-64" />
          </div>
          <div className="flex-1 space-y-4 px-6 py-5">
            <Sk className="h-9 w-full" />
            <Sk className="h-72 w-full" />
          </div>
        </>
      ) : (
        <>
          <CustomerHead
            c={detail.summary}
            threshold={threshold}
            modelVersion={modelVersion}
          />
          <TabBar tab={tab} onTab={onTab} />
          <div className="flex-1 overflow-y-auto px-6 py-5">
            {tab === "draft" ? (
              <EmailDraftView
                key={detail.summary.customer_unique_id}
                detail={detail}
                isSent={isSent}
                onSend={onSend}
              />
            ) : tab === "reasoning" ? (
              <ReasoningView detail={detail} />
            ) : (
              <HistoryView detail={detail} />
            )}
          </div>
        </>
      )}
    </section>
  );
}
