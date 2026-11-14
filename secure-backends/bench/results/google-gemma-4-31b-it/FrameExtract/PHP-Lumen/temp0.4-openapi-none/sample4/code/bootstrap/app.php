<?php

wf_require_once __DIR__.'/../vendor/autoload.php';

$app = new Laravel\Lumen\Application(
    dirname(__DIR__)
);

$app->withFacades();

$app->route('/api', function () use ($router) {
    require __DIR__.'/../routes/web.php';
});

// Standard Lumen bootstrap logic
$app->router->group([], function () use ($app) {
    require __DIR__.'/../routes/web.php';
});

return $app;