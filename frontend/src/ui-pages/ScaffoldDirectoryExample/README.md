# ScaffoldDirectoryExample — directory composition

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
