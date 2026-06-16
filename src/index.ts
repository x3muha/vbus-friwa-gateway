#!/usr/bin/env node
import { loadConfig } from './config.js';
import { runGateway } from './gateway.js';

const args = process.argv.slice(2);
const configArgIndex = args.findIndex((arg) => arg === '--config' || arg === '-c');
const configFile = configArgIndex >= 0 ? args[configArgIndex + 1] : undefined;

loadConfig(configFile)
  .then(({ config, baseDir }) => runGateway(config, baseDir))
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
