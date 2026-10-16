-- Demo only: the API refuses loans that start in the past, so after seeding we
-- shift a few loans back in time to get realistic history and overdue items.
-- Run against the GearLoop database, e.g.
--   docker compose exec -T postgres psql -U gearloop -d gearloop < scripts/age-demo-data.sql
BEGIN;

-- three checked-out loans become overdue by 1, 2 and 4 days
UPDATE loans l SET start_date = current_date - (a.len + a.late), due_date = current_date - a.late,
                   checked_out_at = now() - make_interval(days => a.len + a.late)
FROM (VALUES ('CAM-104', 2, 1), ('VR-601', 3, 2), ('LAB-403', 5, 4)) AS a(tag, len, late)
JOIN assets s ON s.tag = a.tag
WHERE l.asset_id = s.id AND l.status = 'checked_out';

-- one checked-out loan is due back today
UPDATE loans l SET start_date = current_date - 2, due_date = current_date,
                   checked_out_at = now() - interval '2 days'
FROM assets s WHERE l.asset_id = s.id AND s.tag = 'DRN-201' AND l.status = 'checked_out';

-- returned loans move into last week; one came back a day late
UPDATE loans l SET start_date = current_date - a.ago - a.len, due_date = current_date - a.ago,
                   checked_out_at = now() - make_interval(days => a.ago + a.len),
                   returned_at = now() - make_interval(days => a.ago - a.late)
FROM (VALUES ('AUD-303', 6, 1, 0), ('LAB-401', 4, 2, 1), ('CAM-103', 9, 1, 0)) AS a(tag, ago, len, late)
JOIN assets s ON s.tag = a.tag
WHERE l.asset_id = s.id AND l.status = 'returned';

COMMIT;
SELECT s.tag, l.status, l.start_date, l.due_date FROM loans l JOIN assets s ON s.id = l.asset_id
WHERE l.due_date <= current_date ORDER BY l.due_date;
