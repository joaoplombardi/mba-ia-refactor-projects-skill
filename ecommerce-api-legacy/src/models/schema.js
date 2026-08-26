'use strict';

const logger = require('../utils/logger');
const { hashPassword } = require('../utils/passwords');

const TABLES = [
    `CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        name TEXT,
        email TEXT UNIQUE,
        pass TEXT
    )`,
    `CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY,
        title TEXT,
        price REAL,
        active INTEGER
    )`,
    `CREATE TABLE IF NOT EXISTS enrollments (
        id INTEGER PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        course_id INTEGER REFERENCES courses(id)
    )`,
    `CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY,
        enrollment_id INTEGER REFERENCES enrollments(id),
        amount REAL,
        status TEXT
    )`,
    `CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY,
        action TEXT,
        created_at DATETIME
    )`,
];

async function createTables(db) {
    for (const statement of TABLES) {
        await db.run(statement);
    }
    logger.info('Schema verificado');
}

async function seed(db) {
    const existing = await db.get('SELECT COUNT(*) AS total FROM courses');
    if (existing.total > 0) return false;

    await db.transaction(async (tx) => {
        // Development credential only, and hashed on insert.
        await tx.run('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)', [
            'Leonan',
            'leonan@fullcycle.com.br',
            hashPassword('123'),
        ]);
        await tx.run('INSERT INTO courses (title, price, active) VALUES (?, ?, ?), (?, ?, ?)', [
            'Clean Architecture', 997.0, 1,
            'Docker', 497.0, 1,
        ]);
        await tx.run('INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)', [1, 1]);
        await tx.run('INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)', [
            1, 997.0, 'PAID',
        ]);
    });

    logger.info('Seed aplicado');
    return true;
}

module.exports = { createTables, seed };
