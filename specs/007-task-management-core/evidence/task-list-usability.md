# Feature 007 Task-list Usability Evidence

## Status

**PENDING EXTERNAL MODERATED REVIEW**. The privacy-safe protocol and evidence
schema are ready. No participant result has been invented or inferred from
automated tests.

## Acceptance rule

- Recruit at least 10 representative users across HELPDESK, MANAGER, and LEADER.
- Show each participant the same representative Task-list screen containing
  Overdue, Today, Upcoming, and Completed work.
- Without coaching, ask the participant to identify what belongs in each of the
  four groups.
- A participant passes only when all four groups are identified correctly and
  independently.
- SC-011 passes when at least 9 of the first 10 valid sessions pass. If more than
  10 valid sessions are run, report both the first-10 result and the overall
  result; do not discard failures.

## Moderator protocol

1. Use a non-production environment with synthetic Task titles and descriptions.
2. Confirm the participant performs one of the three representative roles, but
   do not record their name, username, email, phone number, employee identifier,
   IP address, GPS data, or free-text comments.
3. Present the Task list at a recorded Asia/Ho_Chi_Minh business date. The screen
   must contain at least one item in every group, including a completed Task whose
   assigned date would otherwise place it in another group.
4. Read this neutral prompt once: "Please identify the work that is overdue, due
   today, upcoming, and completed. Tell me when you are finished."
5. Do not point at a group, explain labels, or correct the participant during the
   attempt. Stop timing when the participant finishes.
6. Record only the aggregate role/count/time/pass fields below. Invalid sessions
   (environment failure or moderator coaching) are counted separately with no
   participant detail and rerun with a new representative participant.
7. Have a second reviewer verify the arithmetic and sign the release decision by
   role/title and UTC time; do not add a personal signature or account identifier.

## Aggregate execution record

- Environment/release candidate: `PENDING`
- Business date (Asia/Ho_Chi_Minh): `PENDING`
- Review run time (UTC): `PENDING`

| Role cohort | Valid sessions | Passed all four | Failed | Median seconds | Maximum seconds |
|---|---:|---:|---:|---:|---:|
| HELPDESK | 0 | 0 | 0 | N/A | N/A |
| MANAGER | 0 | 0 | 0 | N/A | N/A |
| LEADER | 0 | 0 | 0 | N/A | N/A |
| **Total** | **0** | **0** | **0** | **N/A** | **N/A** |

- Invalid sessions excluded and rerun: `0`
- First 10 valid sessions passed: `PENDING/10`
- Overall valid sessions passed: `PENDING/PENDING`
- Result: **NOT EXECUTED**
- Independent arithmetic reviewer role/title: `PENDING`
- Review verified at (UTC): `PENDING`

## Privacy and retention check

- [ ] The record contains aggregate role/count/time/pass data only.
- [ ] No participant identity or contact data was collected.
- [ ] No Task content, credentials, URL tokens, GPS, photo, or device evidence was retained.
- [ ] Any facilitator working notes were destroyed after aggregate verification.

The release gate remains closed until the completed aggregate record proves at
least 10 valid sessions and at least 9 successful first-10 interpretations.
