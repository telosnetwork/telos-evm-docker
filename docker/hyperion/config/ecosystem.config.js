const {addApiServer, addIndexer} = require("./definitions/ecosystem_settings");

module.exports = {
    apps: [
        addIndexer('telos-local-testnet'),
        addApiServer('telos-local-testnet', 1),
        addIndexer('telos-testnet'),
        addApiServer('telos-testnet', 1),
        addIndexer('telos-mainnet'),
        addApiServer('telos-mainnet', 1)
    ]
};
