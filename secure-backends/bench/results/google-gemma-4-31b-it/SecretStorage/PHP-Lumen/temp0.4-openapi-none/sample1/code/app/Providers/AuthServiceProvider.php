<?php

namespace App\Providers;

use App\Models\User;
use Illuminate\Support\ServiceProvider;

class AuthServiceProvider extends ServiceProvider
{
    public function boot()
    {
        $this->app['auth']->viaRequest('api', function ($request) {
            if ($token = $request->bearerToken()) {
                return User::where('token', $token)->first();
            }
            return null;
        });
    }

    public function register()
    {
        //
    }
}