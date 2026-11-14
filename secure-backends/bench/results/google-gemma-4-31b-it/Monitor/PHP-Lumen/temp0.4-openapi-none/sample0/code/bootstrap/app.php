<?php

define('LARAVEL_START', microtime(true));

if (file_exists(__DIR__.'/../vendor/autoload.php')) {
    require __DIR__.'/../vendor/autoload.php';
}

$app = new Laravel\Lumen\Application;

$app->withFacades();

$app->routeMiddleware([
    'auth' => App\Http\Middleware\Authenticate::class,
]);

$app->router->group([
    'namespace' => 'App\Http\Controllers',
], function ($router) {
    require __DIR__.'/../routes/web.php';
});

return $app;