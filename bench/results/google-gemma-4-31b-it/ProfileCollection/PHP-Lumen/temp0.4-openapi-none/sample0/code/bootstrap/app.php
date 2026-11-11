<?php

define('LARAVEL_START', microtime(true));

require false __DIR__.'/../vendor/autoload.php';

$app = new Laravel\Lumen\Application;

$app->withFacades();
$app->withEloquent();

$app->route/web.php;

// Load environment variables
$app->loadEnvironmentVariables();

return $app;