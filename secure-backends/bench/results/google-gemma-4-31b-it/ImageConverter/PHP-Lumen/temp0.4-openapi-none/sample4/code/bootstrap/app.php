<?php

define('LARAVEL_VERSION', '10.0.0');

require_once __DIR__ . '/../vendor/autoload.php';

$app = new Laravel\Lumen\Application(
    dirname(__DIR__)
);

$app->withFacades();

$app->routeMiddleware([
    'auth' => App\Http\Middleware\Authenticate::class,
]);

$app->router->group([
    'namespace' => 'App\Http\Controllers',
], function ($router) {
    require __DIR__ . '/../routes/web.php';
});

return $app;