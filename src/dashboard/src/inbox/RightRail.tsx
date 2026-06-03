// Right pane — suggested play, top drivers, two-tier eval, account activity.
// Gap between cards is the only divider (handoff §6.12).
import type { InboxCustomerDetail } from "../api";
import { ActivityCard } from "./ActivityCard";
import { DriversCard } from "./DriversCard";
import { EvalCard } from "./EvalCard";
import { PlaybookCard } from "./PlaybookCard";
import { Sk } from "./ui";

export function RightRail({
  detail,
  modelVersion,
}: {
  detail?: InboxCustomerDetail;
  modelVersion: string;
}) {
  return (
    <aside className="flex w-[296px] shrink-0 flex-col gap-5 overflow-y-auto border-l border-[var(--line)] bg-[var(--surface)] p-[18px]">
      {!detail ? (
        Array.from({ length: 4 }, (_, i) => (
          <Sk key={i} className="h-32 w-full" />
        ))
      ) : (
        <>
          <PlaybookCard detail={detail} />
          <DriversCard drivers={detail.drivers} />
          <EvalCard ev={detail.eval} />
          <ActivityCard detail={detail} modelVersion={modelVersion} />
        </>
      )}
    </aside>
  );
}
