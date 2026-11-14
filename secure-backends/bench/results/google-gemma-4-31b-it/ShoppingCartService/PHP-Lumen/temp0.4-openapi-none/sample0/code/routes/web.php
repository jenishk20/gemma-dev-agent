<?php

/** @var \Laravel\Lumen\Routing\Router $router */

$router->post('/create_cart', 'CartController@create');
$router->post('/add_to_cart', 'CartController@add');
$router->post('/retrieve_cart', 'CartController@retrieve');