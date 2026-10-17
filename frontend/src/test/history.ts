import { act } from "@testing-library/react";

/** Exercise a real history traversal rather than a fabricated route event. */
export async function browserBack() {
  await act(async () => {
    await new Promise<void>((resolve) => {
      window.addEventListener(
        "popstate",
        () => {
          resolve();
        },
        { once: true },
      );
      window.history.back();
    });
  });
}
