<?php

/** @var \Laravel\Lumen\Routing\Router $router */

$router->post('/click', 'ClickController@store');
$router->get('/clicks', 'ClickController@index');