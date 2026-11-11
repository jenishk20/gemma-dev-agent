<?php

/** @var \Laravel\Lumen\Routing\Router $router */

$router->get('/recommender', 'RecommenderController@index');
$router->post('/recommender', 'RecommenderController@store');