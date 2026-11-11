<?php

/** @var \Laravel\Lumen\Routing\Router $router */

$router->post('/heartbeat', 'ServiceController@heartbeat');
$router->post('/services', 'ServiceController@getServices');