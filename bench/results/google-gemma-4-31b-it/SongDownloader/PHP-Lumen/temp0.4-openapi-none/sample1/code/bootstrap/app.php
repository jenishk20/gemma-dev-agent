<?php

define('LARAVEL_START', microtime(true));

require __DIR__.'/../vendor/autoload.php';

$app = Laravel\Lumen\Application::create(
    realpath(__DIR__.'/../'),
    realpath(__DIR__.'/../vendor')
);

$app->withFacades();

$app->routeFallback(function () {
    return response('Not Found', 404);
});

$app->router->group([
    'namespace' => 'App\Http\Controllers',
], function ($router) {
    require __DIR__.'/../routes/web.php';
});

return $app;