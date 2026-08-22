'use strict';

const { NotFoundError, PaymentDeniedError, ValidationError } = require('../errors/AppError');
const { hashPassword } = require('../utils/passwords');
const logger = require('../utils/logger');

const DEFAULT_PASSWORD_LENGTH = 8;

class CheckoutController {
    constructor({ db, userModel, courseModel, enrollmentModel, paymentModel, auditLogModel, paymentGateway }) {
        this.db = db;
        this.userModel = userModel;
        this.courseModel = courseModel;
        this.enrollmentModel = enrollmentModel;
        this.paymentModel = paymentModel;
        this.auditLogModel = auditLogModel;
        this.paymentGateway = paymentGateway;
    }

    /**
     * Maps the legacy wire format (usr/eml/pwd/c_id/card) onto domain names.
     * The wire format itself is unchanged — renaming it would break clients.
     */
    static parseRequest(body = {}) {
        const { usr: name, eml: email, pwd: password, c_id: courseId, card } = body;

        // Same presence check, same plain-text 400 body as the legacy handler.
        if (!name || !email || !courseId || !card) {
            throw new ValidationError('Bad Request');
        }
        // The legacy code called card.startsWith() without a type check, so a
        // numeric `card` crashed the process from inside an async callback.
        if (typeof card !== 'string') {
            throw new ValidationError('Bad Request');
        }

        return { name, email, password, courseId, card };
    }

    async checkout(body) {
        const input = CheckoutController.parseRequest(body);

        const course = await this.courseModel.findActiveById(input.courseId);
        if (!course) {
            throw new NotFoundError('Curso não encontrado');
        }

        const payment = await this.paymentGateway.charge({
            card: input.card,
            amount: course.price,
        });
        if (payment.status !== 'PAID') {
            throw new PaymentDeniedError('Pagamento recusado');
        }

        // Enrolment, payment and audit trail land together or not at all.
        const enrollmentId = await this.db.transaction(async (tx) => {
            let user = await this.userModel.findByEmail(input.email, tx);
            let userId = user ? user.id : null;

            if (!userId) {
                const rawPassword = input.password || CheckoutController.#generatePassword();
                userId = await this.userModel.create(
                    { name: input.name, email: input.email, passwordHash: hashPassword(rawPassword) },
                    tx,
                );
            }

            const newEnrollmentId = await this.enrollmentModel.create(
                { userId, courseId: input.courseId },
                tx,
            );
            await this.paymentModel.create(
                { enrollmentId: newEnrollmentId, amount: course.price, status: payment.status },
                tx,
            );
            await this.auditLogModel.record(
                `Checkout curso ${input.courseId} por ${userId}`,
                tx,
            );
            return newEnrollmentId;
        });

        logger.info(`Checkout concluído: matrícula ${enrollmentId} no curso ${course.title}`);
        return { msg: 'Sucesso', enrollment_id: enrollmentId };
    }

    /** Random password beats the legacy shared default of "123456". */
    static #generatePassword() {
        return require('crypto').randomBytes(DEFAULT_PASSWORD_LENGTH).toString('hex');
    }
}

module.exports = CheckoutController;
