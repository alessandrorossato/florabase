"""Generate a bounded UI composition without registering routes or inventing an API."""

import argparse
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def scaffold(
    root: Path, name: str, archetype: str, *, dry_run: bool = False
) -> list[Path]:
    if not re.fullmatch(r"[A-Z][A-Za-z0-9]{0,63}", name):
        raise ValueError("NAME must be a PascalCase identifier, at most 64 characters")
    if archetype not in {"directory", "activity"}:
        raise ValueError("ARCHETYPE must be directory or activity")
    base = (root / "frontend/src/ui-pages").resolve()
    if not base.is_relative_to(root.resolve() / "frontend/src"):
        raise ValueError("Output must stay inside frontend/src")
    folder = base / name
    if folder.exists():
        raise FileExistsError(folder)
    if archetype == "directory":
        imports = 'import { useState, type ReactNode } from "react";\nimport { DirectoryPage, DirectoryViewSwitcher, DirectoryRecords } from "../../components/DirectoryPage";\nimport { DirectoryTools, DirectorySearch } from "../../components/DirectoryTools";\nimport type { DirectoryView } from "../../components/directoryPresentation";'
        body = f'''const [view, setView] = useState<DirectoryView>("list");
  const [query, setQuery] = useState("");
  return <DirectoryPage titleId="{name}-title"
    header={{<PageHeader title="{name}" titleId="{name}-title" eyebrow="Implement domain context"
      tools={{<DirectoryTools name="{name}"
        search={{<DirectorySearch id="{name}-search" label="Search records" placeholder="Search records…" value={{query}} onChange={{setQuery}} />}}
        presentation={{<DirectoryViewSwitcher value={{view}} onChange={{setView}} />}}
        filters={{<p>TODO: compose typed domain filters here.</p>}}
      />}}
    />}}
    feedback={{feedback}}
    content={{<DirectoryRecords view={{view}} label="Implement domain records"><li>TODO: connect the owning domain's data, rows/cards and loading/error/empty states.</li></DirectoryRecords>}}
  />;'''
    else:
        imports = 'import { ActivityPage } from "../../components/ActivityPage";'
        body = f'''return <ActivityPage titleId="{name}-title"
    header={{<PageHeader title="{name}" titleId="{name}-title" eyebrow="Implement domain context" />}}
    chronology={{<p>TODO: connect ordered facts with explicit occurrence/recorded-time semantics.</p>}}
  />;'''
    props = (
        "({ feedback }: { feedback?: ReactNode } = {})"
        if archetype == "directory"
        else "()"
    )
    test_source = (
        f"""import {{ cleanup, render, screen }} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {{ afterEach, expect, test, vi }} from "vitest";
import {{ LoadingState, ErrorState }} from "../../components/WorkspaceUI";
import {{ {name} }} from "./{name}";

afterEach(cleanup);
test("keyboard view switching retains search; request feedback uses the house states", async () => {{
  const user = userEvent.setup();
  const {{ rerender }} = render(<{name} />);
  await user.type(screen.getByRole("searchbox", {{name: "Search records"}}), "Aloe");
  screen.getByRole("button", {{name: "Gallery"}}).focus();
  await user.keyboard(" ");
  expect(screen.getByRole("button", {{name: "Gallery", pressed: true}})).toHaveFocus();
  expect(screen.getByRole("searchbox")).toHaveValue("Aloe");
  rerender(<{name} feedback={{<LoadingState>Loading records…</LoadingState>}} />);
  expect(screen.getByRole("status")).toHaveTextContent("Loading records");
  const retry = vi.fn();
  rerender(<{name} feedback={{<ErrorState onRetry={{retry}}>Could not load records</ErrorState>}} />);
  await user.click(screen.getByRole("button", {{name: "Retry"}}));
  expect(retry).toHaveBeenCalledOnce();
  expect(screen.getByRole("searchbox")).toHaveValue("Aloe");
}});
"""
        if archetype == "directory"
        else """import { test } from "vitest";

test.todo("Implement domain occurrence/recorded-time, loading, empty, error and long-name acceptance");
test.todo("Verify keyboard names, selection/focus, URL/back and supported Saved Views");
"""
    )
    files = {
        f"{name}.tsx": f"""import {{ PageHeader }} from "../../components/ReferenceUI";
{imports}

export function {name}{props} {{
  {body}
}}
""",
        f"{name}.test.tsx": test_source,
        "README.md": f"""# {name} — {archetype} composition

This scaffold is deliberately unfinished. Register no production route until domain acceptance is implemented.
Use the existing PageHeader/DirectoryTools, semantic tokens and house controls. The domain owns requests,
mutations, filtering, reference pickers and validation. Directory mode is controlled; when attached to a
supported surface use useDirectoryPresentation, preserving canonical filters and selection. New surfaces
need an explicit state contract before gaining Saved Views. Do not invent backend routes.

Replace TODO regions, implement tests, and manually integrate the route. Keep meaningful labels,
44px controls, truthful unknown/partial values, focus return and image fallback. Verify 1440×844,
1024×844 and 390×844 plus light/dark. Run focused Vitest and TypeScript checks; use CI-004 policy for delivery.
Working examples: frontend/src/ui-lab/Lab.tsx (DirectoryPage and ActivityPage). make ui-lab opens the local lab.
Request state is supplied through the feedback slot using LoadingState/ErrorState; the parent owns retry.
For forms reuse EditWorkspace, FormSections, existing reference pickers and field-validation focus.
The generated keyboard/state test is template coverage, not completed domain acceptance.
""",
    }
    paths = [folder / file for file in files]
    if dry_run:
        return paths
    folder.mkdir(parents=True, exist_ok=False)
    written: list[Path] = []
    try:
        for file, text in files.items():
            path = folder / file
            with path.open("x") as output:
                output.write(text)
            written.append(path)
    except OSError:
        for path in written:
            path.unlink()
        folder.rmdir()
        raise
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default=os.environ.get("FLORABASE_UI_PAGE_NAME"))
    parser.add_argument(
        "--archetype",
        choices=["directory", "activity"],
        default=os.environ.get("FLORABASE_UI_PAGE_ARCHETYPE"),
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.name or not args.archetype:
        parser.error("NAME and ARCHETYPE are required")
    try:
        paths = scaffold(ROOT, args.name, args.archetype, dry_run=args.dry_run)
    except (ValueError, FileExistsError) as error:
        parser.error(str(error))
    for path in paths:
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
