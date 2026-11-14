<?php

require __DIR__.'/../vendor/autoload.php';

$app = new Laravel\Lumen\Application(
    dirname(__DIR__)
);

$app->withFacades();

$app->routeFallback(function () {
    return response()->json(['error' => 'Not Found'], 404);
});

$app->router->group([], function ($router) {
    require __DIR__.'/../routes/web.php';
});

return $app;