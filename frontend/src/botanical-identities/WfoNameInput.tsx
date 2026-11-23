import { useEffect, useRef, useState, type InputHTMLAttributes } from "react";
import type { ProtectedRequestCapability } from "../auth/api";
import { searchNames } from "../taxonomy/api";

/** Scientific-name input suggesting names from the local WFO index; free text stays valid. */
export function WfoNameInput({
  capability,
  ...input
}: InputHTMLAttributes<HTMLInputElement> & {
  id: string;
  capability: ProtectedRequestCapability;
}) {
  const field = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState(
    typeof input.defaultValue === "string" ? input.defaultValue : "",
  );
  // A form reset changes the value without an input event; follow it.
  useEffect(() => {
    const form = field.current?.form;
    if (!form) return;
    const follow = () => {
      window.setTimeout(() => {
        setQuery(field.current?.value ?? "");
      });
    };
    form.addEventListener("reset", follow);
    return () => {
      form.removeEventListener("reset", follow);
    };
  }, []);
  const [found, setFound] = useState({ prefix: "", names: [] as string[] });
  const prefix = query.trim();
  useEffect(() => {
    if (prefix.length < 2) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      searchNames(prefix, capability, controller.signal)
        .then((candidates) => {
          setFound({
            prefix,
            names: [
              ...new Set(candidates.map(({ taxon }) => taxon.scientific_name)),
            ],
          });
        })
        .catch(() => {
          // An unavailable index only removes suggestions; typing is unaffected.
          setFound({ prefix, names: [] });
        });
    }, 250);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [prefix, capability]);
  // Suggestions from an older prefix are never shown for the current text.
  const names = found.prefix === prefix ? found.names : [];
  const listId = `${input.id}-wfo-suggestions`;
  return (
    <>
      <input
        {...input}
        ref={field}
        list={listId}
        autoComplete="off"
        onChange={(event) => {
          setQuery(event.currentTarget.value);
          input.onChange?.(event);
        }}
      />
      <datalist id={listId}>
        {names.map((name) => (
          <option key={name} value={name} />
        ))}
      </datalist>
    </>
  );
}
