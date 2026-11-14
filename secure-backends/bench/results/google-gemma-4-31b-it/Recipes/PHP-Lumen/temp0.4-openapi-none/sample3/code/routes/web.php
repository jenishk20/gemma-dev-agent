<?php

/** @var \Laravel\Lumen\Routing\Router $router */

$router->get('/recipes', 'RecipeController@index');
$router->post('/recipes/upload', 'RecipeController@store');
$router->get('/recipes/{recipeId}', 'RecipeController@show');
$router->post('/recipes/{recipeId}/comments', 'RecipeController@addComment');
$router->post('/recipes/{recipeId}/ratings', 'RecipeController@addRating');