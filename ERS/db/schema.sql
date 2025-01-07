CREATE DATABASE elective_system;

USE elective_system;

CREATE TABLE hod (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);


CREATE TABLE elective_selections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(5),
    elective_id INT,
    student_name VARCHAR(255),
    department VARCHAR(255),
    FOREIGN KEY (student_id) REFERENCES students(id),
    FOREIGN KEY (elective_id) REFERENCES electives(id)
);
