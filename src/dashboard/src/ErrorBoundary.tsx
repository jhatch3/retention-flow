// App-level error boundary — a render throw anywhere below shows a recoverable
// fallback instead of white-screening the whole dashboard.
import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}
interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Surface to the console for debugging; a real deployment would ship this
    // to an error tracker here.
    console.error("Dashboard render error:", error, info.componentStack);
  }

  render(): ReactNode {
    const { error } = this.state;
    if (!error) return this.props.children;
    return (
      <div className="grid h-screen place-items-center bg-[var(--bg)] p-6 text-center">
        <div className="max-w-md rounded-lg border border-[var(--line)] bg-[var(--surface)] p-6">
          <div className="text-[15px] font-semibold text-[var(--risk)]">
            Something went wrong rendering this view.
          </div>
          <p className="mt-2 text-[12.5px] text-[var(--fg-mute)]">{error.message}</p>
          <button
            type="button"
            onClick={() => this.setState({ error: null })}
            className="mt-4 rounded-md border border-[var(--line)] bg-[var(--surface)] px-4 py-2 text-[13px] font-medium text-[var(--fg)] hover:border-[var(--fg-mute)]"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }
}
