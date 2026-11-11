<?php

define('LARAVEL_START', microtime(true));

require false __DIR__.'/../vendor/autoload.php';

$app = new Laravel\Lumen\Application;

$app->withFacades();

$app->routeFallback(function () {
    return response('Not Found', 404);
});

$app->router->group([], function ($router) {
    require __DIR__.'/../routes/web.php';
});

return $app;