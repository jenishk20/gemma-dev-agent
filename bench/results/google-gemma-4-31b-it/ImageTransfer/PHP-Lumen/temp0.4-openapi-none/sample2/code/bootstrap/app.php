<?php

define('LARAVEL_START', microtime(true));

require __DIR__.'/../vendor/autoload.php';

$app = new Laravel\Lumen\Application(
    dirname(__DIR__)
);

$app->withFacades();

$app->withEloquent();

if (file_exists('.env')) {
    Dotenv\Dotenv::createImmutable(dirname(__DIR__))->load();
}

return $app;