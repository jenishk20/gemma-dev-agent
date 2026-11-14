<?php

/** @var \Laravel\Lumen\Routing\Router $router */

$router->get('/entries', 'WikiController@index');
$router->post('/entries', 'WikiController@store');
$router->get('/entries/{entryId}', 'WikiController@show');
$router->put('/entries/{entryId}', 'WikiController@update');
$router->get('/entries/{entryId}/edits', 'WikiController@history');

// UI Helper for editing
$router->get('/entries/edit/{entryId}', 'WikiController@editForm');