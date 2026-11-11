<?php

namespace App\Providers;

use App\Models\User;
use Illuminate\Support\ServiceProvider;
use Illuminate\Support\Facades\Auth;
use Illuminate\Http\Request;

class AuthServiceProvider extends ServiceProvider
{
    public function boot()
    {
        Auth::viaRequest('api', function (Request $request) {
            $cookie = $request->cookie('AUTH_COOKIE');
            if ($cookie) {
                // In a real app, we'd decrypt/verify a session token. 
                // For this simple implementation, we store the user ID in the cookie.
                return User::find($cookie);
            }
            return null;
        });
    }
}