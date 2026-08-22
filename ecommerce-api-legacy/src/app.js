'use strict';

/**
 * Composition root.
 *
 * The only module that wires the pieces together: it loads config, opens the
 * database, builds models, injects them into controllers, then registers routes
 * and — last — the error handler.
 */
const express = require('express');

const { config, validate } = require('./config');
const Database = require('./models/Database');
const { createTables, seed } = require('./models/schema');
const UserModel = require('./models/UserModel');
const CourseModel = require('./models/CourseModel');
const EnrollmentModel = require('./models/EnrollmentModel');
const PaymentModel = require('./models/PaymentModel');
const AuditLogModel = require('./models/AuditLogModel');
const { PaymentGateway } = require('./services/PaymentGateway');
const CheckoutController = require('./controllers/CheckoutController');
const ReportController = require('./controllers/ReportController');
const UserController = require('./controllers/UserController');
const registerRoutes = require('./routes');
const { errorHandler, notFoundHandler } = require('./middlewares/errorHandler');
const logger = require('./utils/logger');

async function buildApp({ db: injectedDb, paymentGateway: injectedGateway } = {}) {
    validate();

    const db = injectedDb || Database.open(config.dbFile);
    await createTables(db);
    if (config.seedOnBoot) {
        await seed(db);
    }

    const userModel = new UserModel(db);
    const courseModel = new CourseModel(db);
    const enrollmentModel = new EnrollmentModel(db);
    const paymentModel = new PaymentModel(db);
    const auditLogModel = new AuditLogModel(db);

    const paymentGateway = injectedGateway
        || new PaymentGateway({
            apiKey: config.payment.gatewayKey,
            approvedCardPrefix: config.payment.approvedCardPrefix,
        });

    const controllers = {
        checkout: new CheckoutController({
            db, userModel, courseModel, enrollmentModel, paymentModel, auditLogModel, paymentGateway,
        }),
        report: new ReportController({ courseModel, enrollmentModel }),
        user: new UserController({ db, userModel, enrollmentModel, paymentModel }),
    };

    const app = express();
    app.use(express.json());

    registerRoutes(app, controllers);

    app.use(notFoundHandler);
    app.use(errorHandler);

    app.locals.db = db;
    return app;
}

async function start() {
    const app = await buildApp();
    return app.listen(config.port, () => {
        logger.info(`LMS API rodando na porta ${config.port}`);
    });
}

if (require.main === module) {
    start().catch((error) => {
        logger.error('Falha ao iniciar a aplicação', error);
        process.exit(1);
    });
}

module.exports = { buildApp, start };
