# Troubleshooting

This page covers everyday questions that can come up while using Florabase in your browser or on a
phone.

## Signed out while editing a form

If your sign-in session expires while you are typing in a form or dialog, Florabase does **not**
throw away your work or reload the page. Instead, a **Session expired — sign in again** dialog opens
on top of the screen while keeping your unsaved edits in place behind it:

1. In the **Session expired — sign in again** dialog, check your **Login name** and enter your
   **Password**.
2. Click **Sign in**.
3. The dialog closes and you return directly to the form you were editing, with all of your text and
   selections still intact.
4. Click the form's save button (such as **Save changes**, **Add entry**, or **Save profile**) to
   finish saving.

(If you do not want to keep the edits on screen, click **Discard unsaved changes and sign out**
instead.)

<!-- TODO(DOC-04 screenshot): Session expired — sign in again dialog over an open form, highlight Login name, Password, Sign in, and Discard unsaved changes and sign out -->

## "Nothing saved" or a server / connection error appears

If your home network drops or the Florabase server restarts while you click a save button:

- Florabase shows a clear error banner in the form or dialog explaining that the change could not be
  saved.
- Your typed notes, dates, and selections stay on screen so you do not have to retype them.
- Nothing is half-saved or silently duplicated.
- Once your network connection or server is back, click the form's save button again. If you are
  unsure whether a save completed right before a disconnection, open the directory or record in
  another tab to check before saving a second time.

## Changing your password or recovering a forgotten password

### When you are signed in and want to change your password

1. In the left rail, open **Settings** → **Account** (on a phone, tap **Account and settings** at the
   top right, then **Account**).
2. Under **Change password**, enter your **Current password**, your **New password** (at least 12
   characters), and **Confirm new password**.
3. Click **Change password**.
4. Florabase confirms `Password changed.` Any other browsers or devices signed in to your account
   will be asked to sign in again with the new password.

### When you have forgotten your password and cannot sign in

Because Florabase is self-hosted and private, it does not send password-reset emails over the
internet. If you forget your password, ask the person who operates your Florabase server to run the
offline password-reset command described in the [Installation and operations
guide](../installation.md).

## A page or directory shows no records

If you open **Seeds**, **Sowings**, **Cuttings**, **Plants**, **Harvests**, or **Locations** and do
not see a record you know you created, check the active search and filters:

1. **Check the search box**: clear any text in the search field at the top of the directory.
2. **Check active filter chips**: look right below the toolbar for active filter chips (such as
   `Lifecycle: Active`, `State: Active`, or a specific location or botanical identity).
3. **Check whether the record moved to History**:
   - By default, collection directories show **Active** records so completed sowings, exhausted seed
     lots, depleted stored material, reintegrated plants, and reversed records stay out of your way.
   - To see historical records, click **Filters**, change **Lifecycle** (or **State**) to `All` (or
     to the specific historical status such as `Exhausted`, `Completed`, `Depleted`, `Reintegrated`,
     or `Reversed`), and click **Done** (or click **Reset** in the **Filters** drawer).

## Using Florabase on a phone or tablet

Florabase works in any modern mobile browser on phones and tablets without installing a separate
native app:

- **Mobile navigation**: on narrow screens, the bottom bar gives you one-tap access to **Today**,
  **Collection**, **Record**, **Activity**, and **Explore**. The top bar switches between pages
  inside the current workspace, opens **Search and commands**, and opens **Account and settings**
  (which includes **Suppliers**, **Orders**, **Account**, **Theme**, **Labels**,
  **Import / Export**, **Data sources**, **Help**, and **Sign out**).
- **Installing to your Home Screen**: you can add Florabase to your phone's Home Screen so it opens
  in its own window like an app.
- **Important note for iPhone and iPad (iOS / iPadOS)**: when you add Florabase to the iOS Home
  Screen, iOS gives the Home Screen icon its own separate sign-in storage from Safari. You will need
  to sign in once inside the Home Screen app even if you were already signed in inside Safari.
- **Requires a live connection**: Florabase always reads and writes directly to your server so your
  records are never out of sync; an active network connection to your Florabase server is required.

For full details on mobile browsers and Home Screen installation, see the [Mobile and PWA
guide](../pwa.md).
