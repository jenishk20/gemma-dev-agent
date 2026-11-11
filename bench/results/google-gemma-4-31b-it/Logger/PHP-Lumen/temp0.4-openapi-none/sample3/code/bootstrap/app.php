<?php

namespace Laravel\Lumen;

(require_once __DIR__.'/../vendor/autoload.php');

$app = new Application(
    dirname(__DIR__)
);

$app->withFacades();

$app->router->group([
    'namespace' => 'App\Http\Controllers',
], function ($router) {
    require __DIR__.'/../routes/web.php';
});

return $app;