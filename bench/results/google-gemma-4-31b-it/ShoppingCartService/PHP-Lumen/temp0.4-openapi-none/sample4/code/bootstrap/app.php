<?php

define('LARAVEL_START', microtime(true));

require __DIR__.'/../vendor/autoload.php';

$app = new Laravel\Lumen\Application();

$app->withFacades();

$app->withEloquent();

$app->routeFallback(function () {
    return response()->json(['error' => 'Not Found'], 404);
});

return $app;