'use strict';

/**
 * Domain errors. Controllers throw these; the error middleware maps them to HTTP.
 *
 * `body` preserves the legacy response format: this API answers errors with
 * plain text, not JSON, and the refactor does not change the wire contract.
 */
class AppError extends Error {
    constructor(message, statusCode = 500, body = null) {
        super(message);
        this.name = this.constructor.name;
        this.statusCode = statusCode;
        this.body = body === null ? message : body;
        Error.captureStackTrace(this, this.constructor);
    }
}

class ValidationError extends AppError {
    constructor(message, body) {
        super(message, 400, body);
    }
}

class NotFoundError extends AppError {
    constructor(message, body) {
        super(message, 404, body);
    }
}

class PaymentDeniedError extends AppError {
    constructor(message, body) {
        super(message, 400, body);
    }
}

module.exports = { AppError, ValidationError, NotFoundError, PaymentDeniedError };
