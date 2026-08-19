# Approved MobiFone header assets

Source supplied by the product owner in repository `/assets` on 2026-08-20.
The copies in this directory are unchanged deployable public assets; their
SHA-256 values match the supplied originals.

| File               | Format   | Intrinsic size | Intended use          | SHA-256                                                            |
| ------------------ | -------- | -------------: | --------------------- | ------------------------------------------------------------------ |
| `logo-phone.jpg`   | JPEG     |    1436 × 1026 | compact phone header  | `841d6f39bb1d953e325e68e6921c89f6ffc20d3a70d11a5eaf6995655fdefb60` |
| `logo-desktop.png` | PNG RGBA |      659 × 400 | tablet/desktop header | `048790f1d1d479b7763a1fbeecbcf5e1eade930392acdb49045cbce01d092035` |

Do not crop, stretch, recolor, trace, or replace these files with a remote URL.
`MobiFoneLogo` selects the intended responsive variant and renders it with
intrinsic dimensions plus `object-fit: contain`.
