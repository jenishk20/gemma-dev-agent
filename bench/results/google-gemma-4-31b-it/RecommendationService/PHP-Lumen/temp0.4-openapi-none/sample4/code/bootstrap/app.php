<?php

define('LARAVEL_START', microtime(true));

require_once __DIR__.'/../vendor/autoload.php';

$app = new Laravel\Lumen\Application;

$app->withFacades();

$app->withEloquent();

$app->routeFallback(function () {
    return response('Not Found', 404);
});

$app->router->group([
    'namespace' => 'App\Http\Controllers',
], function ($router) {
    require __DIR__.'/../routes/web.php';
});

return $app;