import { Component, ErrorInfo, ReactNode } from "react";

type Props = { children: ReactNode };
type State = { hasError: boolean };

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("CivicPulse UI error", error, info);
  }

  render() {
    if (this.state.hasError) {
      return <main className="page-shell"><section className="result"><div><p className="kicker">Something went wrong</p><h2>Please reload the report form.</h2></div></section></main>;
    }
    return this.props.children;
  }
}
