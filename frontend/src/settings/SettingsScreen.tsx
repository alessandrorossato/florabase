import { PageHeader } from "../components/ReferenceUI";
import { Page } from "../components/WorkspaceUI";
import "./settings.css";
import { AppearanceSettings } from "../appearance/AppearanceSettings";

/**
 * Theme (route #/settings, kept for compatibility): palette and appearance for this
 * browser only. The QR destination lives with Labels, and Labels and Import / Export are
 * reached from the Settings navigation, so this page no longer repeats them (M8 final).
 */
export function SettingsScreen() {
  return (
    <Page className="settings-workspace" titleId="settings-heading">
      <PageHeader
        title="Theme"
        titleId="settings-heading"
        eyebrow="Settings"
        description="Palette and appearance for this browser."
      />
      <div className="settings-content">
        <AppearanceSettings />
      </div>
    </Page>
  );
}
