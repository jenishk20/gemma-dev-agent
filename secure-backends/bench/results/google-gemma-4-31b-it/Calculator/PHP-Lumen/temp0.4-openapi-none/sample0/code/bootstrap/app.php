<?php

define('LARAVEL_START', microtime(true));

require_once __DIR__ . '/../vendor/autoload.php';

$app = new Laravel\Lumen\Application();

$app->withFacades();

$app->route('/calculator', function () {
    // This is handled in routes/web.php
});

$app->configure('app');

return $app;