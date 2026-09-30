import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import { FormSections } from "./FormSections";
afterEach(cleanup);
const panels = [
  {
    id: "essentials",
    label: "Essentials",
    content: (
      <label>
        Name
        <input name="name" id="name" required />
      </label>
    ),
  },
  {
    id: "notes",
    label: "Notes",
    content: (
      <label>
        Notes
        <textarea name="notes" aria-label="Profile notes" />
      </label>
    ),
  },
];
test("tabs and Back/Next retain native values and submit the complete form only once", async () => {
  const submit = vi.fn(
    (event: React.SyntheticEvent<HTMLFormElement, SubmitEvent>) => {
      event.preventDefault();
      return new FormData(event.currentTarget);
    },
  );
  render(
    <form onSubmit={submit}>
      <FormSections
        panels={panels}
        submit={<button type="submit">Save</button>}
        cancel={<button type="button">Cancel</button>}
      />
    </form>,
  );
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Name"), "Okra");
  expect(
    screen.queryByRole("button", { name: "Save" }),
  ).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Next" }));
  await user.type(screen.getByLabelText("Profile notes"), "Keep dry");
  await user.click(screen.getByRole("button", { name: "Back" }));
  expect(screen.getByLabelText("Name")).toHaveValue("Okra");
  expect(submit).not.toHaveBeenCalled();
  await user.click(screen.getByRole("tab", { name: "Notes" }));
  expect(screen.getByLabelText("Profile notes")).toHaveValue("Keep dry");
  await user.click(screen.getByRole("button", { name: "Save" }));
  expect(submit).toHaveBeenCalledTimes(1);
  expect(Object.fromEntries(submit.mock.results[0].value as FormData)).toEqual({
    name: "Okra",
    notes: "Keep dry",
  });
});
test("native validation reveals and focuses the first invalid hidden panel", async () => {
  render(
    <form>
      <FormSections
        panels={panels}
        submit={<button>Save</button>}
        cancel={null}
      />
    </form>,
  );
  const user = userEvent.setup();
  await user.click(screen.getByRole("tab", { name: "Notes" }));
  await user.click(screen.getByRole("button", { name: "Save" }));
  expect(screen.getByRole("tab", { name: "Essentials" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  expect(screen.getByLabelText("Name")).toHaveFocus();
});
test("server validation reveals its exact field and arrow/Home/End navigation uses roving focus", async () => {
  const props = {
    panels,
    submit: <button>Save</button>,
    cancel: null,
    errorFields: [{ match: /name/i, selector: "#name" }],
  };
  const { rerender } = render(<FormSections {...props} />);
  const user = userEvent.setup();
  await user.click(screen.getByRole("tab", { name: "Essentials" }));
  await user.keyboard("{End}");
  expect(screen.getByRole("tab", { name: "Notes" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await waitFor(() => {
    expect(screen.getByRole("tab", { name: "Notes" })).toHaveFocus();
  });
  rerender(
    <FormSections
      {...props}
      error={{ field: "name", messages: ["Invalid name"] }}
    />,
  );
  await waitFor(() => {
    expect(screen.getByLabelText("Name")).toHaveFocus();
  });
  expect(screen.getAllByRole("tabpanel")).toHaveLength(1);
  fireEvent.keyDown(screen.getByRole("tab", { name: "Essentials" }), {
    key: "ArrowRight",
  });
  expect(screen.getByRole("tab", { name: "Notes" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
});
