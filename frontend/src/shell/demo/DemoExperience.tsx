import { useCallback, useEffect, useRef, useState } from "react";

import "./demo.css";
import { subscribeDemoReadOnlyBlocked } from "./readonlyNotice";
import {
  DEMO_INSTALL_URL,
  DEMO_TOUR_STEPS,
  hasExplicitTourParam,
  readTourDismissed,
  writeTourDismissed,
} from "./tourSteps";

export interface DemoExperienceProps {
  onNavigate: (href: string) => void;
}

export function DemoExperience({ onNavigate }: DemoExperienceProps) {
  const [tourOpen, setTourOpen] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    if (hasExplicitTourParam(window.location.search, window.location.hash)) {
      return true;
    }
    return !readTourDismissed();
  });
  const [stepIndex, setStepIndex] = useState(0);
  const [blockedMessage, setBlockedMessage] = useState<string | null>(null);
  const tourTitleRef = useRef<HTMLHeadingElement>(null);
  const tourStartedRef = useRef(false);

  useEffect(() => {
    let timeoutId: number | undefined;
    const unsubscribe = subscribeDemoReadOnlyBlocked((message) => {
      setBlockedMessage(message);
      if (timeoutId !== undefined) window.clearTimeout(timeoutId);
      timeoutId = window.setTimeout(() => {
        setBlockedMessage(null);
      }, 6500);
    });
    return () => {
      unsubscribe();
      if (timeoutId !== undefined) window.clearTimeout(timeoutId);
    };
  }, []);

  const currentStep = DEMO_TOUR_STEPS[stepIndex];

  const goToStep = useCallback(
    (nextIndex: number) => {
      const clamped = Math.max(
        0,
        Math.min(DEMO_TOUR_STEPS.length - 1, nextIndex),
      );
      setStepIndex(clamped);
      onNavigate(DEMO_TOUR_STEPS[clamped].href);
    },
    [onNavigate],
  );

  const dismissTour = useCallback(() => {
    setTourOpen(false);
    writeTourDismissed(true);
  }, []);

  const startTour = useCallback(() => {
    writeTourDismissed(false);
    setTourOpen(true);
    goToStep(0);
  }, [goToStep]);

  useEffect(() => {
    if (!tourOpen) {
      tourStartedRef.current = false;
      return;
    }
    if (!tourStartedRef.current) {
      tourStartedRef.current = true;
      onNavigate(DEMO_TOUR_STEPS[stepIndex].href);
    }
    tourTitleRef.current?.focus();
  }, [tourOpen, stepIndex, onNavigate]);

  useEffect(() => {
    if (!tourOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        dismissTour();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [tourOpen, dismissTour]);

  const isFirst = stepIndex === 0;
  const isLast = stepIndex === DEMO_TOUR_STEPS.length - 1;

  return (
    <>
      <div
        className="demo-banner"
        role="region"
        aria-label="Public demo notice"
      >
        <div className="demo-banner__meta">
          <span className="demo-banner__badge">Read-only demo</span>
          <p className="demo-banner__text">
            Sample botanical collection · Changes are disabled
          </p>
        </div>
        <div className="demo-banner__actions">
          <button
            type="button"
            className="button--secondary"
            onClick={startTour}
          >
            {tourOpen ? "Restart tour" : "Start guided tour"}
          </button>
          <a
            className="demo-banner__install"
            href={DEMO_INSTALL_URL}
            target="_blank"
            rel="noopener noreferrer"
          >
            Install Florabase
          </a>
        </div>
      </div>

      {blockedMessage && (
        <div className="demo-readonly-notice" role="status" aria-live="polite">
          <p>{blockedMessage}</p>
          <button
            type="button"
            className="button--secondary"
            onClick={() => {
              setBlockedMessage(null);
            }}
          >
            Dismiss
          </button>
        </div>
      )}

      {tourOpen && (
        <aside
          className="demo-tour"
          role="region"
          aria-label="Interactive guided tour"
        >
          <div className="demo-tour__header">
            <div>
              <p className="demo-tour__eyebrow">
                {`Step ${String(stepIndex + 1)} of ${String(DEMO_TOUR_STEPS.length)} · ${currentStep.workspaceLabel}`}
              </p>
              <h2 className="demo-tour__title" ref={tourTitleRef} tabIndex={-1}>
                {currentStep.title}
              </h2>
            </div>
            <button
              type="button"
              className="demo-tour__close"
              aria-label="Close guided tour"
              onClick={dismissTour}
            >
              ×
            </button>
          </div>

          <div
            className="demo-tour__dots"
            role="group"
            aria-label="Tour progress"
          >
            {DEMO_TOUR_STEPS.map((step, index) => (
              <button
                key={step.id}
                type="button"
                className={`demo-tour__dot${
                  index === stepIndex
                    ? " demo-tour__dot--current"
                    : index < stepIndex
                      ? " demo-tour__dot--done"
                      : ""
                }`}
                aria-label={`Go to step ${String(index + 1)}: ${step.title}`}
                aria-current={index === stepIndex ? "step" : undefined}
                onClick={() => {
                  goToStep(index);
                }}
              />
            ))}
          </div>

          <p className="demo-tour__body">{currentStep.body}</p>
          <p className="demo-tour__hint">{currentStep.hint}</p>

          <div className="demo-tour__footer">
            <button
              type="button"
              className="button--quiet"
              onClick={dismissTour}
            >
              Skip tour
            </button>
            <div className="demo-tour__nav">
              {!isFirst && (
                <button
                  type="button"
                  className="button--secondary"
                  onClick={() => {
                    goToStep(stepIndex - 1);
                  }}
                >
                  Back
                </button>
              )}
              {isLast ? (
                <>
                  <a
                    className="demo-banner__install"
                    href={DEMO_INSTALL_URL}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Install Florabase
                  </a>
                  <button type="button" onClick={dismissTour}>
                    Explore freely
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  onClick={() => {
                    goToStep(stepIndex + 1);
                  }}
                >
                  Next
                </button>
              )}
            </div>
          </div>
        </aside>
      )}
    </>
  );
}
