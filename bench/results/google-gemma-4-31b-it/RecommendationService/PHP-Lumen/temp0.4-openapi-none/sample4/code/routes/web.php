<?php

/** @var \Laravel\Lumen\Routing\Router $router */

$router->get('/recommender', 'RecommenderController@getProducts');
$router->post('/recommender', 'RecommenderController@storeProduct');