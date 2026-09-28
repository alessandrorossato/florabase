import { Component, type ReactNode } from "react";

import { WorkspaceChunkLoadError } from "./workspaceChunk";

// A route chunk can fail to download while the authenticated shell is still usable.
export class WorkspaceBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };

  static getDerivedStateFromError(error: unknown) {
    if (!(error instanceof WorkspaceChunkLoadError)) throw error;
    return { failed: true };
  }

  render() {
    if (this.state.failed) {
      return (
        <div className="notice notice--error" role="alert">
          <p>Florabase could not load this workspace.</p>
          <button
            type="button"
            onClick={() => {
              window.location.reload();
            }}
          >
            Reload and try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
