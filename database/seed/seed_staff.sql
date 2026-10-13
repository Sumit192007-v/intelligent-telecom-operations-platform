-- Optional: staff members for the "Assign Complaint" dropdown.
-- Login has been removed, so password_hash is just an unused placeholder.
-- Run:  mysql -u root -p telecom_operations < database/seed/seed_staff.sql
USE telecom_operations;

INSERT INTO users (name, email, password_hash, role, department) VALUES
  ('Network Engineer',  'network.staff@local.invalid',   '', 'staff', 'Network'),
  ('Technical Support', 'technical.staff@local.invalid', '', 'staff', 'Technical'),
  ('Billing Agent',     'billing.staff@local.invalid',   '', 'staff', 'Billing'),
  ('Support Agent',     'support.staff@local.invalid',   '', 'staff', 'Customer Support')
ON DUPLICATE KEY UPDATE name = VALUES(name);
