import type { ComponentProps } from "react";
import { openCollectionPage } from "../components/recordNavigation";

/** Canonical creation page with the identity hub retained as its return context. */
export function IdentityTaskLink(
  props: ComponentProps<"a"> & { href: string },
) {
  return (
    <a
      {...props}
      onClick={(event) => {
        if (
          event.button !== 0 ||
          event.metaKey ||
          event.ctrlKey ||
          event.altKey ||
          event.shiftKey
        )
          return;
        event.preventDefault();
        openCollectionPage(props.href, window.location.hash);
      }}
    />
  );
}
