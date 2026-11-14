<?php

/** @var \Laravel\Lumen\Routing\Router $router */

$router->post('/associate_card', 'CardController@associate');
$router->post('/retrieve_cards', 'CardController@retrieve');