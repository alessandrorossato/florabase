import type { ReactNode } from "react";
import { calendarDate, dayLabel, monthLabel, shiftMonth } from "./calendar";
import { localDay, type ScheduleState } from "./state";

export function ScheduleNavigation({
  state,
  today,
  switcher,
  onChange,
}: {
  state: ScheduleState;
  today: string;
  switcher: ReactNode;
  onChange: (state: ScheduleState) => void;
}) {
  const selected =
    state.date || (today.startsWith(state.month) ? today : `${state.month}-01`);
  const month = state.view === "calendar";
  function choose(date: string) {
    onChange({ ...state, date, month: date.slice(0, 7) });
  }
  function shift(delta: number) {
    if (month)
      onChange({ ...state, month: shiftMonth(state.month, delta), date: "" });
    else {
      const date = calendarDate(selected);
      date.setDate(date.getDate() + delta * 7);
      choose(localDay(date));
    }
  }
  const monday = calendarDate(selected);
  monday.setDate(monday.getDate() - ((monday.getDay() + 6) % 7));
  const days = Array.from({ length: 7 }, (_, i) => {
    const date = new Date(monday);
    date.setDate(date.getDate() + i);
    return localDay(date);
  }).filter((date) => /^(?!0000)\d{4}-/.test(date));
  return (
    <>
      <div className="schedule-view-heading">
        <h3>{monthLabel(state.month)}</h3>
        {switcher}
      </div>
      <nav className="schedule-period-bar" aria-label="Planning dates">
        <div className="actions">
          <button
            className="button--secondary"
            disabled={
              month ? state.month === "0001-01" : selected <= "0001-01-07"
            }
            onClick={() => {
              shift(-1);
            }}
          >
            Previous {month ? "month" : "week"}
          </button>
          <button
            className="button--secondary"
            onClick={() => {
              choose(today);
            }}
          >
            Today
          </button>
          <button
            className="button--secondary"
            disabled={
              month ? state.month === "9999-12" : selected >= "9999-12-24"
            }
            onClick={() => {
              shift(1);
            }}
          >
            Next {month ? "month" : "week"}
          </button>
          <label className="schedule-jump">
            Jump to date
            <input
              type="date"
              min="0001-01-01"
              max="9999-12-31"
              value={selected}
              onChange={(e) => {
                if (e.target.validity.valid && e.target.value)
                  choose(e.target.value);
              }}
            />
          </label>
          {!month && state.date && (
            <button
              className="button--quiet"
              onClick={() => {
                onChange({ ...state, date: "" });
              }}
            >
              All dates
            </button>
          )}
        </div>
        {!month && (
          <div className="schedule-date-strip">
            {days.map((date) => (
              <button
                className="button--secondary"
                key={date}
                aria-label={dayLabel(date)}
                aria-pressed={state.date === date}
                aria-current={date === today ? "date" : undefined}
                onClick={() => {
                  choose(date);
                }}
              >
                <span>
                  {calendarDate(date).toLocaleDateString("en-GB", {
                    weekday: "short",
                  })}
                </span>
                <strong>{Number(date.slice(-2))}</strong>
                <span>
                  {date === today
                    ? "Today"
                    : calendarDate(date).toLocaleDateString("en-GB", {
                        month: "short",
                      })}
                </span>
              </button>
            ))}
          </div>
        )}
      </nav>
    </>
  );
}
