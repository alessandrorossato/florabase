// TypeScript's DOM declaration still requires the two legacy methods.
export function createMediaQueryList(
  media: string,
  matches: boolean,
): MediaQueryList {
  return Object.assign(new EventTarget(), {
    media,
    matches,
    onchange: null,
    addListener: () => undefined,
    removeListener: () => undefined,
  });
}
