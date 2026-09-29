CREATE DATABASE IF NOT EXISTS telecom_operations;

USE telecom_operations;

CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM(
        'customer',
        'support_agent',
        'engineer',
        'manager',
        'staff'
    ) NOT NULL,
    department VARCHAR(50) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS complaints (
    id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL,
    complaint_type VARCHAR(50) NOT NULL,
    subject VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    latitude DOUBLE DEFAULT NULL,
    longitude DOUBLE DEFAULT NULL,
    department VARCHAR(50) DEFAULT NULL,
    priority ENUM(
        'Low',
        'Medium',
        'High',
        'Critical'
    ) DEFAULT 'Medium',
    status ENUM(
        'Pending',
        'Assigned',
        'In Progress',
        'Resolved',
        'Closed'
    ) DEFAULT 'Pending',
    assigned_to INT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (customer_id)
        REFERENCES users(id),

    FOREIGN KEY (assigned_to)
        REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS network_measurements (
    id INT PRIMARY KEY AUTO_INCREMENT,
    operator VARCHAR(50) NOT NULL,
    timestamp DATETIME NOT NULL,
    latitude DOUBLE NOT NULL,
    longitude DOUBLE NOT NULL,
    download_mbps DOUBLE,
    upload_mbps DOUBLE,
    rtt_ms DOUBLE,
    network_technology VARCHAR(50),
    `5g_frequency_mhz` DOUBLE,
    `5g_pci` INT,
    lte_earfcn INT,
    cell_event VARCHAR(100)
);