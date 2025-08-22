# Planning and Documentation

This document captures the design decisions, entity-relationship
diagram (ERD), database comparisons, feedback notes, and
rationale for the Foundations of Resilience Tracker project.

## ERD and Normalisation
Below is the entity‑relationship diagram (ERD) for the Resilience
Tracker. The diagram was provided in the assignment brief and is
embedded here for reference. It shows five core tables:

1. **Client (User)** – Each client has an ID, first and last name, email
   and is assigned the `CLIENT` role. Counsellors are also stored in
   this table with the `COUNSELLOR` role.
2. **Habit** – The master list of habits. Each habit has a unique
   identifier, name and description.
3. **ClientHabit** – A junction table linking users to habits. It
   allows a client to track multiple habits, optionally with a custom
   label and display order. Unique constraints ensure a client cannot
   assign the same habit twice and that display order is unique per
   client.
4. **WeeklyAssessment** – A weekly check‑in for a client. Each
   assessment stores the week’s start date (e.g. Monday), the
   calculated wellbeing score (average of habit scores), an optional
   reflection comment, and a timestamp when the assessment was
   submitted.
5. **HabitScore** – A per‑habit rating within a weekly assessment.
   Each record references the associated `WeeklyAssessment` and
   `ClientHabit`, stores the score (0–10) and an optional note.

This design adheres to third normal form (3NF). All non‑key
attributes (e.g. `name`, `description`, `order`, `score`) depend only
on their table’s primary key and not on one another. The
many‑to‑many relationship between clients and habits is broken out
into the `ClientHabit` table. Weekly assessments and habit scores
reference their parent entities through foreign keys. By storing the
overall wellbeing score as a computed column, we avoid recomputing it
on every read and maintain proper normalisation.

![ERD diagram](../ERP.png)

## Database Choice Comparison

When choosing between relational and NoSQL databases we evaluated the
structure of our data and the types of queries the application must
support. The Resilience Tracker has multiple related entities
(`Client`, `Habit`, `ClientHabit`, `WeeklyAssessment` and
`HabitScore`) that require referential integrity and complex joins. A
relational database is therefore the natural choice.

We considered SQLite versus PostgreSQL for the relational engine. SQLite
is a lightweight file‑based database that excels for single‑user,
embedded applications. However, because it locks the entire database
file on write, it does not handle concurrent connections well. A
comparison article notes that PostgreSQL supports multiple concurrent
connections and offers more robust data types and security features
compared with SQLite【626417802003760†L1189-L1218】. SQLite is fast for simple
operations but lacks advanced concurrency and reliability features
available in PostgreSQL【626417802003760†L1190-L1210】.

We also weighed the option of a document database such as MongoDB. NoSQL
databases can scale horizontally and are excellent for unstructured
data, but they do not natively support joins. Articles point out that
Postgres is more suitable for applications with complex business logic
and query requirements, whereas MongoDB shines when the data model is
simple and denormalised【877936117778791†L299-L302】. Our application
requires ensuring uniqueness (e.g. one assessment per client per week,
one habit assignment per client), aggregating scores across tables and
enforcing referential integrity—all of which are simpler in a
relational schema. Consequently, PostgreSQL is the preferred choice
for both development and production deployments.

## Feedback Log

### 2025‑08‑18 – Peer review

We shared an early draft of the ERD and API surface with two peers. The
first reviewer suggested storing the wellbeing score in the
`WeeklyAssessment` table rather than calculating it on each request, to
avoid recalculating across potentially large tables. This change was
accepted and implemented by adding a `wellbeing_score` column and
recomputing it only when scores are added, updated or deleted.

The second reviewer pointed out that permanently deleting records
would make it difficult to audit historical data. Their suggestion was
to implement **soft deletes** by adding a `deleted_at` timestamp to
each table. This way, deleted clients, habits, assessments and
scores are simply marked as inactive rather than removed. Queries that
list data now filter on `deleted_at is null`. The `soft_delete_service`
module was added to encapsulate the logic for cascading soft deletes.

### 2025‑08‑20 – Mentor feedback

Our mentor recommended adding input sanitisation to avoid cross‑site
scripting (XSS) when storing user comments and notes. We added a
`strip_tags` function in `app/util/sanitization.py` to remove HTML tags
from the `overall_comment` and `note` fields before persisting them.

They also highlighted the importance of enforcing business rules in
the service layer rather than scattering logic across route
handlers. As a result, we created a `wellbeing_service` to compute
average scores and a `soft_delete_service` to cascade soft deletions.

Finally, we were advised to adopt pagination parameters (`limit` and
`offset`) on list endpoints and to handle date filtering for
assessments. These suggestions were implemented in the `list_clients`
and `list_client_assessments` routes.