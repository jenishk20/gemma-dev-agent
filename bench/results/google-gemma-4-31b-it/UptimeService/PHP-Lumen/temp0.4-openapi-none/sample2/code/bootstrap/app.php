<?php

define('LARAVEL_START', microtime(true));

require false __DIR__.'/../vendor/autoload.php';

$app = Laravel\Lumen\Application::bootstrap();

$app->withFacades();

$app->withEloquent();

return $app;