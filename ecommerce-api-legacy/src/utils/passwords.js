'use strict';

const crypto = require('crypto');

/**
 * Password hashing with scrypt from the Node standard library — no new dependency.
 *
 * Replaces `badCrypto()`, which repeated the first two base64 characters of the
 * password 10.000 times and truncated to 10 chars: unsalted, non-reversible only
 * by accident, and with almost no entropy.
 */
const KEY_LENGTH = 64;
const SALT_BYTES = 16;

function hashPassword(rawPassword) {
    const salt = crypto.randomBytes(SALT_BYTES).toString('hex');
    const derived = crypto.scryptSync(String(rawPassword), salt, KEY_LENGTH).toString('hex');
    return `scrypt$${salt}$${derived}`;
}

function verifyPassword(storedHash, rawPassword) {
    if (typeof storedHash !== 'string') return false;
    const [scheme, salt, expected] = storedHash.split('$');
    if (scheme !== 'scrypt' || !salt || !expected) return false;

    const actual = crypto.scryptSync(String(rawPassword), salt, KEY_LENGTH).toString('hex');
    const a = Buffer.from(actual, 'hex');
    const b = Buffer.from(expected, 'hex');
    return a.length === b.length && crypto.timingSafeEqual(a, b);
}

module.exports = { hashPassword, verifyPassword };
