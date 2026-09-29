ALTER TABLE users
    MODIFY role ENUM(
        'customer',
        'support_agent',
        'engineer',
        'manager',
        'staff'
    ) NOT NULL,
    ADD COLUMN department VARCHAR(50) DEFAULT NULL;

ALTER TABLE complaints
    ADD COLUMN latitude DOUBLE DEFAULT NULL,
    ADD COLUMN longitude DOUBLE DEFAULT NULL;