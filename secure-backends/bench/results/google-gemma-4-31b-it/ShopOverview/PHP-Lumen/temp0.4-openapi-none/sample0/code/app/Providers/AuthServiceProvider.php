<?php

namespace App\Providers;

use App\Models\User;
use Illuminate\Support\ServiceProvider;

class AuthServiceProvider extends ServiceProvider
{
    public function boot()
    {
        $this->app['auth']->viaRequest(function ($request) {
            $cookie = $request->cookie('AUTH_COOKIE');
            if ($cookie) {
                // In a real app, we'd use a session store or JWT. 
                // For this simple task, we treat the cookie value as the user ID.
                return User::find($cookie);
            }
            return null;
        });
    }
}