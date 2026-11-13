/**
 * Date controls a form must not save past: an incomplete PartialDateField draft or an
 * unanswered date choice. They report null like "unknown", so a `noValidate` form asks
 * here; each control's `validationMessage` says what is missing.
 */
export function invalidDateControls(form: HTMLFormElement): HTMLInputElement[] {
  return [...form.elements].filter(
    (control): control is HTMLInputElement =>
      control instanceof HTMLInputElement &&
      control.dataset.dateControl !== undefined &&
      control.validity.customError,
  );
}

/** FormSections `errorFields` entry that reveals and focuses the control named above. */
export const invalidDateErrorField = {
  match: /is incomplete: enter a valid/,
  selector: "input[data-date-control]:invalid",
};

/**
 * True while a date field holds typed input that is not yet a value. The form state still
 * reads null there, so dirty checks that compare form state must also ask this.
 */
export function hasDateDraft(form: HTMLFormElement | null): boolean {
  return Boolean(
    form &&
    invalidDateControls(form).some(
      (control) => control.dataset.dateControl !== "choice",
    ),
  );
}
