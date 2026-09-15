# Strange Wolves website editor

## Approved design restore point

The exact approved public website, including every image, is preserved at:

https://github.com/shanegavin91/Strangewolves.ie/tree/approved-design-2026-09-15

GitHub snapshot commit: `32115156ff29960f8dbb547436d04ee7d70d502d`.
Local source tag: `approved-design-2026-09-15`, pointing to `4dbc633cfd87cb8adafb04f7e1aacd1719fca8ba`.

Restore `dist/` from that snapshot to recover the complete approved static site. The snapshot contains no editor dependency. The test site is CloudFront distribution `E3GYT8ZA7PP315`, backed by `strangewolves-ie-site-544795558099` in `eu-west-1`. Do not change the separate strangewolves.ie production distribution or DNS.

## Editor

Entry: `/admin/index.html`. Cognito invitation-only sign-in uses authorization code + PKCE. HTTP API JWT validation is mandatory; Lambda additionally requires the `editors` group and access-token claim. No public user registration is enabled. An editor account still needs to be created for the email Shane chooses; no invitation has been sent.

The public layout remains static. `editor-schema.json` identifies permitted plain-text and image fields. `content-editor.js` safely applies published content through textContent, alt attributes and constrained same-origin image URLs. If loading fails, the approved static HTML remains usable.

Drafts and history live in a separate private S3 bucket. Published content is `/content/site.json`; image uploads are `/uploads/`. The normal website deployment must never delete or overwrite these editor-managed paths. Every publish first archives the previous content. Conditional writes reject stale edits. History is loaded into a draft; restoring requires a deliberate Publish action.

The Lambda code has access only to draft/history, published content, new image uploads and its own logs. It cannot rewrite HTML/CSS, delete files, grant users access or access member/payment data. Photos become publicly accessible after upload; upload only photos intended for the club website. Raw SVG uploads are rejected.

`build_content.py` extracts the initial values from the approved HTML. Run it only when intentionally extending the schema; do not reset live content from its generated baseline. Package `handler.py` and `dist/editor-schema.json` together as the Lambda ZIP. `provision.py` provides the idempotent AWS Core resource setup function. `resources.json` records non-secret resource IDs after provisioning.

## Next phases — not enabled yet

1. Invitation-managed administrator accounts and a short real-user editor check.
2. New-member popup: contact details, experience, clear privacy information and the club-approved waiver. Store personal records privately with access controls and retention rules.
3. Class registration: individual dated sessions, capacity, bookings, cancellations, duplicate prevention, waiting list if required, and a coach attendance view. Preserve Monday/Thursday 8 PM and Saturday 11 AM, Europe/Dublin timezone. Initially €10 paid on arrival.
4. Payments: hosted checkout, server-verified webhooks, payment/refund state and idempotency. Never collect card numbers inside this editor. Keep financial status separate from attendance.

Do not present member registration, waiver acceptance or payments as active until these flows are implemented and tested.
