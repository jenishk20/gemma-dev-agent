<?php

define('LARAVEL_START', microtime(true));

require_once __DIR__.'/../vendor/autoload.php';

$app = new Laravel\Lumen\Application;

$app->withFacades();

$app->withEloquent();

$app->route(/routes/web.php);

return $app;