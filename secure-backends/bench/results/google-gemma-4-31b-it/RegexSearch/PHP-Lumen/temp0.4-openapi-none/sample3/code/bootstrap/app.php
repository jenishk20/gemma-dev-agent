<?php

define('LARAVEL_START', microtime(true));

require __DIR__.'/../vendor/autoload.php';

$app = new Laravel\Lumen\Application(
    dirname(__DIR__)
);

$app->withFacades();

$app->withEloquent();

if (file_exists(__DIR__.'/../.env')) {
    (new Dotenv\Dotenv(__DIR__.'/../'))->load();
}

if ($app->environment('local')) {
    // enable concise error reporting
}

$app->router->group([], function ($router) {
    require __DIR__.'/../routes/web.php';
});

return $app;