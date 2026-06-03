// Triage Inbox data hooks — raw fetch + useState/useEffect, matching the rest
// of the dashboard (no TanStack Query).
import { useEffect, useState } from "react";
import { api } from "../api";
import type { FilterKey, InboxCustomerDetail, InboxCustomerList } from "../api";

interface Async<T> {
  data?: T;
  loading: boolean;
  error?: string;
}

/** The at-risk queue for a given filter. `refetch()` forces a reload. */
export function useInboxQueue(filter: FilterKey) {
  const [state, setState] = useState<Async<InboxCustomerList>>({ loading: true });
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    let alive = true;
    setState((s) => ({ data: s.data, loading: true }));
    api.inbox
      .customers(filter)
      .then((data) => alive && setState({ data, loading: false }))
      .catch((e) => alive && setState({ loading: false, error: String(e) }));
    return () => {
      alive = false;
    };
  }, [filter, nonce]);

  return { ...state, refetch: () => setNonce((n) => n + 1) };
}

/** Full triage detail for one customer; idle when `id` is null. */
export function useInboxCustomer(id: string | null): Async<InboxCustomerDetail> {
  const [state, setState] = useState<Async<InboxCustomerDetail>>({ loading: false });

  useEffect(() => {
    if (!id) {
      setState({ loading: false });
      return;
    }
    let alive = true;
    setState({ loading: true });
    api.inbox
      .customer(id)
      .then((data) => alive && setState({ data, loading: false }))
      .catch((e) => alive && setState({ loading: false, error: String(e) }));
    return () => {
      alive = false;
    };
  }, [id]);

  return state;
}
