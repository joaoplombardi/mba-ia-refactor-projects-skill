'use strict';

/**
 * Application configuration. Every value comes from the environment.
 *
 * The legacy src/utils.js carried a live payment gateway key, a production
 * database password and SMTP credentials as literals. Those are gone; the
 * only defaults here are development-safe placeholders.
 */

function asBool(raw, fallback = false) {
    if (raw === undefined || raw === null || raw === '') return fallback;
    return ['1', 'true', 'yes', 'on'].includes(String(raw).trim().toLowerCase());
}

const config = {
    env: process.env.NODE_ENV || 'development',
    port: Number(process.env.PORT || 3000),
    dbFile: process.env.DB_FILE || ':memory:',
    seedOnBoot: asBool(process.env.SEED_ON_BOOT, true),
    logLevel: process.env.LOG_LEVEL || 'info',
    payment: {
        // No default: a missing key must fail loudly rather than ship a fake one.
        gatewayKey: process.env.PAYMENT_GATEWAY_KEY || '',
        // Preserves the legacy approval rule so the api.http examples keep working.
        approvedCardPrefix: process.env.APPROVED_CARD_PREFIX || '4',
    },
};

config.isProduction = config.env === 'production';

function validate() {
    if (config.isProduction && !config.payment.gatewayKey) {
        throw new Error('PAYMENT_GATEWAY_KEY must be set in production');
    }
}

module.exports = { config, validate };
