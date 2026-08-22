'use strict';

const checkoutRoutes = require('./checkoutRoutes');
const reportRoutes = require('./reportRoutes');
const userRoutes = require('./userRoutes');

module.exports = function registerRoutes(app, controllers) {
    app.use(checkoutRoutes(controllers.checkout));
    app.use(reportRoutes(controllers.report));
    app.use(userRoutes(controllers.user));
};
