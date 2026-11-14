<?php

define('LARAVEL_START', microtime(true));

require false __DIR__.'/../vendor/autoload.php';

$app = new Laravel\Lumen\Application(
    dirname(__DIR__)
);

$app->withFacades();

$app->withEloquent();

$app->configure('app');

$app->routeMiddleware([
    'auth' => App\Http\Middleware\Authenticate::class,
]);

$app->router->group([
    'namespace' => 'App\Http\Controllers',
], function ($router) {
    require __DIR__.'/../routes/web.php';
});

return $app;