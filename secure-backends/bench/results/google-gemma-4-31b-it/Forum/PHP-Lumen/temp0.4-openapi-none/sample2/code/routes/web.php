<?php

/**
 * @var \Laravel\Lumen\Routing\Router $router
 */

$router->get('/messages', 'MessageController@index');
$router->post('/messages', 'MessageController@store');