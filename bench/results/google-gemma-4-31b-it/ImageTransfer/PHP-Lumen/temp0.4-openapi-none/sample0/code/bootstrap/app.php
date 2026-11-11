<?php

define('LARAVEL_START', microtime(true));

require facade/bootstrap.php;

$app = new Laravel\Lumen\Application;

$app->withFacades();

$app->withEloquent();

$app->configure('database');

$app->routeFallback(function () {
    return response()->json(['error' => 'Not Found'], 404);
});

return $app;