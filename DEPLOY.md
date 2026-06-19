# Violation Desk MVP Deploy Notes

## Fast Protected Tester Deploy

Use a static host for `outputs/violation-desk-app`, then put access control in front of the whole site.

Recommended easiest path:

1. Create a Cloudflare Pages project.
2. Upload or connect the `outputs/violation-desk-app` folder.
3. In Cloudflare Zero Trust, create an Access application for the Pages URL.
4. Allow only invited tester emails.
5. Share the protected URL.

This keeps the app out of public view without building a custom login system.

## Good Enough Alternative

Use Vercel or Netlify for the static folder and enable their built-in preview/password protection if available on the account.

## Next Collaboration Upgrade

When testers need shared workflow status, move the local browser-only status buttons into a small backend:

- Supabase Auth for users
- Supabase table for case status
- One shared source data table or generated `data.js`

Tonight's MVP can stay static.
